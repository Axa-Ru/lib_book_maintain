# -------------------------------------------------------------
# module: src/author_class.py
# -------------------------------------------------------------

import re
import logging
from pathlib import Path
from series_class import Series


class Author:
    """Класс, описывающий каталог автора и управляющий его структурой."""

    def __init__(self, folder_path: Path):
        self.folder_path = folder_path

        # Храним строго точное физическое имя папки с диска "как есть"
        self.name = folder_path.name

        # Поле целевого состояния для переименований (по умолчанию совпадает с текущим)
        self.new_name = folder_path.name

        self.series_list = []

        # Виртуальная серия для одиночных книг, лежащих прямо в корне автора
        self.virtual_series = Series(name="")

        # Виртуальная серия сразу линкуется в общий список,
        # делая одиночные книги корня на 100% видимыми для всех шагов дедупликации!
        self.series_list = [self.virtual_series]

    def _normalize_name(self):
        """
        Реализация очистки и трансформации имени автора.
        1. Унифицирует апострофы и капитализирует О'Генри (буква после ' становится заглавной).
        2. Распознает и склеивает иностранные приставки де/ле/фон/ван через дефис (де-Биржерак).
        """
        import re
        from src.utils import normalize_apostrophes

        # Сначала локально приводим все виды апострофов внутри строки к машинному стандарту '
        working_str = normalize_apostrophes(self.new_name)

        # Разбиваем очищенную строку по пробелам и точкам
        tokens = re.split(r'[.\s]+', working_str.strip())
        sp_name = [token for token in tokens if token]

        # Список иностранных приставок, требующих склеивания (в нижнем регистре)
        foreign_prefixes = {"да", "де", "ле", "фон", "ван"}

        merged_tokens = []
        skip_next = False

        for i, token in enumerate(sp_name):
            if skip_next:
                skip_next = False
                continue

            token_lower = token.lower()

            # КЕЙС 2: Если текущее слово — приставка, и после него есть фамилия
            if token_lower in foreign_prefixes and i < len(sp_name) - 1:
                next_token = sp_name[i + 1]
                # Склеиваем: приставка маленькая, фамилия — с заглавной
                clean_token = f"{token_lower}-{next_token.lower().capitalize()}"
                skip_next = True
            else:
                # КЕЙС 1: Обработка апострофов (например, о'генри -> О'Генри)
                if "'" in token:
                    # Находим позицию машинного апострофа
                    parts = token.split("'", 1)
                    # Первая часть (О), сам апостроф, вторая часть с заглавной буквы (Генри)
                    part_before = parts[0].lower().capitalize()
                    part_after = parts[1].lower().capitalize()
                    clean_token = f"{part_before}'{part_after}"
                elif "-" in token:
                    # Обычная двойная фамилия (Загранная-Омская)
                    sub_parts = token.split("-")
                    clean_token = "-".join(part.lower().capitalize() for part in sub_parts)
                else:
                    # Обычное одиночное слово или инициал
                    clean_token = token.lower().capitalize()

            merged_tokens.append(clean_token)

        # Собираем итоговую строку, расставляя инициалы по вашему стандарту
        result = []
        for i, token in enumerate(merged_tokens):
            is_current_initial = (len(token) == 1)
            result.append(token)

            if is_current_initial:
                result.append(".")

            if i < len(merged_tokens) - 1:
                next_token = merged_tokens[i + 1]
                is_next_initial = (len(next_token) == 1)
                if is_current_initial and is_next_initial:
                    continue
                result.append(" ")

        self.new_name = "".join(result)

    def _compare_name_author(self, other_author: 'Author') -> bool:
        """
        [Версия 0.9.3] Внутренний лингвистический барьер сопоставления ФИО.
        Сравнивает текущего автора со сторонним по их целевым состояниям (new_name).

        Правила совместимости:
        1. Фамилия должна совпадать железно (ё->е).
        2. Имя и Отчество: если есть у обоих — должны совпадать или быть инициалами.
        3. Если у одного отсутствует Имя/Отчество — считаются совместимыми (пропуск дальше).
        """
        # Разбиваем вычисленные идеальные имена обоих авторов на токены в нижнем регистре
        tokens1 = re.split(r'[.\s]+', self.new_name.strip())
        tokens2 = re.split(r'[.\s]+', other_author.new_name.strip())

        t1 = [t.lower() for t in tokens1 if t]
        t2 = [t.lower() for t in tokens2 if t]

        if not t1 or not t2:
            return False

        # Нормализуем букву 'ё' -> 'е'
        t1_norm = [t.replace('ё', 'е').strip() for t in t1]
        t2_norm = [t.replace('ё', 'е').strip() for t in t2]

        # === БАРЬЕР 1: Жесткая проверка Фамилии (Индекс 0) ===
        if t1_norm[0] != t2_norm[0]:
            return False  # Разные фамилии — сразу жесткий отказ

        def _is_token_compatible(tok1: str, tok2: str) -> bool:
            if len(tok1) == 1 or len(tok2) == 1:
                return tok1.startswith(tok2) or tok2.startswith(tok1)
            return tok1 == tok2

        # === БАРЬЕР 2: Проверка Имени (Индекс 1) ===
        if len(t1_norm) > 1 and len(t2_norm) > 1:
            if not _is_token_compatible(t1_norm[1], t2_norm[1]):
                return False  # Разные имена (Иван и Петр) — жесткий отказ

        # === БАРЬЕР 3: Проверка Отчества (Индекс 2) ===
        if len(t1_norm) > 2 and len(t2_norm) > 2:
            if not _is_token_compatible(t1_norm[2], t2_norm[2]):
                return False  # Разные отчества (Маратовна и Ивановна) — жесткий отказ

        # Грамматическая совместимость ФИО полностью доказана
        return True


    def compute_new_name(self, base_lang: str = "ru"):
        """
        [Версия 0.9.3] Вычисляет идеальное имя автора.
        Последовательность выровнена: Сначала абстрактный санитайзер,
        затем точечная лингвистическая трансформация ФИО.
        """
        from utils import sanitize_text_base

        # 1. Базовый абстрактный санитайзер (пробелы, концевые точки, буквы-двойники)
        self.new_name = sanitize_text_base(self.name, base_lang=base_lang)

        # 2. Профессиональная обработка ФИО (апострофы, де-Биржерак, заглавные буквы)
        self._normalize_name()



    def _compare_author_name(self, other_author: 'Author') -> int:
        """Сравнивает длину имен авторов для определения приоритета ФИО."""
        len_self = len(re.sub(r'[^a-zA-Zа-яА-ЯёЁ]', '', self.new_name))
        len_other = len(re.sub(r'[^a-zA-Zа-яА-ЯёЁ]', '', other_author.new_name))
        return 1 if len_self >= len_other else 2

    def is_same_as(self, other_author: 'Author', config: dict) -> bool:
        """
        [Версия 0.9.3] Главный метод сопоставления авторов.
        Реализует каскадный алгоритм: Лингвистический барьер -> Серии -> Книги.
        """
        # === ШАГ 1: Лингвистический барьер (Проверка совместимости ФИО) ===
        if not self._compare_name_author(other_author):
            return False  # Разные фамилии/имена — сразу жесткий отказ, защита тезок

        # Строим списки токенов для быстрой проверки полного тождества
        import re
        t1 = [t.lower().replace('ё', 'е') for t in re.split(r'[.\s]+', self.new_name.strip()) if t]
        t2 = [t.lower().replace('ё', 'е') for t in re.split(r'[.\s]+', other_author.new_name.strip()) if t]

        # === ШАГ 2: Полное тождество ФИО ===
        if t1 == t2:
            return True  # ФИО совпали буква-в-букву — это гарантированно один человек

        # === ШАГ 3: Пересечение названий серий (Для совместимых, но не равных ФИО) ===
        for my_series in self.series_list:
            if my_series.is_virtual:
                continue
            for other_series in other_author.series_list:
                if other_series.is_virtual:
                    continue

                # Нечеткое сравнение названий серий (например, Сетерра == Сетерра)
                # Вызываем оригинальный метод нечеткого сопоставления имени папки серии
                if my_series._check_name_similarity(other_series.new_name, config):
                    return True  # Найдено совпадение хотя бы по одной серии — одобряем слияние!

        # === ШАГ 4: Пересечение по файлам книг (Последняя надежда) ===
        # Собираем абсолютно все книги первого автора (из корня и из подпапок)
        all_my_books = []
        for s in self.series_list:
            all_my_books.extend(s.books)

        # Собираем абсолютно все книги второго автора
        all_other_books = []
        for s in other_author.series_list:
            all_other_books.extend(s.books)

        # Перекрестное сопоставление книг по их чистому title
        for my_book in all_my_books:
            for other_book in all_other_books:
                if my_book.is_same_as(other_book):
                    return True  # Совпало хотя бы одно произведение — одобряем слияние!

        # === ШАГ 5: Если ни одна проверка не увенчалась успехом ===
        return False

    def join_with(self, other_author: 'Author') -> bool:
        """Физически переносит содержимое текущего автора в каталог главного автора."""
        import shutil

        if not self.folder_path.exists() or not other_author.folder_path.exists():
            return False

        # Перенос реальных папок серий
        for my_series in list(self.series_list):
            if my_series.is_virtual:
                continue

            target_series_path = other_author.folder_path / my_series.name

            if not target_series_path.exists():
                try:
                    shutil.move(str(self.folder_path / my_series.name), str(other_author.folder_path))
                    other_author.series_list.append(my_series)
                except Exception:
                    return False
            else:
                other_series_obj = next((s for s in other_author.series_list if s.name == my_series.name), None)
                if other_series_obj:
                    my_series.join_with(other_series_obj, other_author.folder_path)

        # Перенос одиночных книг из корня
        my_virtual = next((s for s in self.series_list if s.is_virtual), None)
        other_virtual = next((s for s in other_author.series_list if s.is_virtual), None)

        if my_virtual and other_virtual:
            my_virtual.join_with(other_virtual, other_author.folder_path)

        # Удаление опустевшего каталога
        try:
            self.folder_path.rmdir()
            return True
        except OSError:
            return False

    def scan_contents(self, book_cfg: dict = None):
        """Сканирует папку автора, разделяя книги на одиночные и серийные."""
        from book_class import Book

        if not self.folder_path.is_dir():
            return

        if book_cfg is None:
            book_cfg = {}

        # Определяем код языка на основе структуры папок (#library/ru/А/Автор -> "ru")
        try:
            lang = self.folder_path.parent.parent.name.lower().strip()
            if lang not in ("ru", "en"):
                lang = "ru"
        except Exception:
            lang = "ru"

        for item in self.folder_path.iterdir():
            # Одиночные книги
            if item.is_file() and item.suffix.lower() == '.epub':
                book = Book(file_path=item, series=self.virtual_series)
                self.virtual_series.books.append(book)

            # Папки серий
            elif item.is_dir():
                real_series = Series(name=item.name)
                self.series_list.append(real_series)

                for file in item.iterdir():
                    if file.is_file() and file.suffix.lower() == '.epub':
                        book = Book(file_path=file, series=real_series)
                        real_series.books.append(book)
