import re
import shutil
import logging
from pathlib import Path
from typing import Dict, List
from series_class import Series
from book_class import Book
from utils import debug_string_character_codes

# Настройка логирования для вывода ошибок
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

class Author:
    """Класс, описывающий каталог автора и управляющий его структурой."""
    def __init__(self, folder_path: Path):
        self.folder_path = folder_path
        self.name = folder_path.name
        self.series_list: List[Series] = []

        # Сразу создаем одну виртуальную серию для одиночных книг автора
        self.virtual_series = Series(name="")
        self.series_list.append(self.virtual_series)


    def scan_contents(self, book_cfg: dict = None):
        """Сканирует папку автора, разделяя книги на одиночные и серийные, сразу наполняя их метаданными."""
        if not self.folder_path.is_dir():
            return

        # Если конфигурация не передана (например, при изолированном тесте),
        # используем пустой словарь, чтобы метод get() внутри Book не упал
        if book_cfg is None:
            book_cfg = {}

        for item in self.folder_path.iterdir():
            # Одиночные книги в корне каталога автора
            if item.is_file() and item.suffix.lower() == '.epub':
                book = Book(file_path=item, series=self.virtual_series)

                # 🔥 Наполняем атрибуты книги сразу при чтении
                book.sanitize_name(book_cfg)

                self.virtual_series.books.append(book)

            # Книги внутри подпапок-серий
            elif item.is_dir():
                real_series = Series(name=item.name)
                self.series_list.append(real_series)

                for file in item.iterdir():
                    if file.is_file() and file.suffix.lower() == '.epub':
                        book = Book(file_path=file, series=real_series)

                        # 🔥 Наполняем атрибуты книги сразу при чтении
                        book.sanitize_name(book_cfg)

                        real_series.books.append(book)


    def join_with(self, other_author: 'Author') -> bool:
        """Реализация функции join_authors в ООП стиле."""
        if not self.folder_path.is_dir() or not other_author.folder_path.is_dir():
            return False

        # Собираем абсолютно все файлы книг текущего автора (из всех его серий)
        all_my_books: List[Book] = []
        for series in self.series_list:
            all_my_books.extend(series.books)

        for my_book in all_my_books:
            try:
                # В ООП-логике, если книга серийная, целевой путь должен вести
                # в подпапку серии внутри каталога второго автора, либо в его корень.
                if my_book.series.is_virtual:
                    target_folder = other_author.folder_path
                else:
                    target_folder = other_author.folder_path / my_book.series.name
                    target_folder.mkdir(exist_ok=True) # Создаем папку серии, если её нет

                other_book_path = target_folder / my_book.path.name

                # ПРОВЕРКА: Если целевого файла нет, просто перемещаем книгу
                if not other_book_path.is_file():
                    shutil.move(str(my_book.path), str(target_folder))
                    continue  # Переходим к следующей книге

                # Сравниваем книги
                result = my_book.compare_with(other_book_path)

                if result == 0:
                    shutil.move(str(my_book.path), str(target_folder))
                elif result == 1:
                    if other_book_path.exists():
                        other_book_path.unlink()
                    shutil.move(str(my_book.path), str(target_folder))
                elif result == 2:
                    my_book.path.unlink()

            except PermissionError:
                logging.error(f"Ошибка доступа при обработке файла: {my_book.path.name}")
                return False
            except Exception as e:
                logging.error(f"Ошибка перемещения книги {my_book.path.name}: {e}")
                return False

        # Перед удалением папки автора нужно сначала удалить пустые папки серий внутри неё
        for item in list(self.folder_path.iterdir()):
            if item.is_dir():
                try:
                    item.rmdir()
                except OSError:
                    pass # Пропускаем, если папка серии почему-то не пуста

        # По завершении удаляем пустой исходный каталог автора
        try:
            self.folder_path.rmdir()
            return True
        except Exception as e:
            logging.error(f"Не удалось удалить каталог автора {self.folder_path}: {e}")
            return False


    def _normalize_name(self):
        """Реализация очистки имени автора.
           Приводит написание имени к правильным формам.
        """
        # Исправлено: берем имя из self.name
        tokens = re.split(r'[.\s]+', self.name.strip())

        # Фильтруем список, убирая пустые строки
        sp_name = [token for token in tokens if token]

        result = []

        # Исправлено: перебираем отфильтрованный список sp_name
        for i, token in enumerate(sp_name):
            clean_token = token.lower().capitalize()
            is_current_initial = (len(clean_token) == 1)

            result.append(clean_token)

            if is_current_initial:
                result.append(".")

            # Исправлено: проверяем границы по списку sp_name
            if i < len(sp_name) - 1:
                next_token = sp_name[i + 1]
                is_next_initial = (len(next_token) == 1)

                if is_current_initial and is_next_initial:
                    continue

                result.append(" ")

        self.name = "".join(result)


    def _is_same_author(self, tokens1: list, tokens2: list) -> int:
        """
        Проверяет сходство ФИО двух авторов.
        Возвращает:
        0 — Авторы разные.
        1 — Имена совпали ПОЛНОСТЬЮ (с точностью до буквы 'ё').
        2 — Имена ПОХОЖИ (инициалы, сокращения). Требуется проверка контекста.
        """
        if not tokens1 or not tokens2:
            return 0

        # Приводим к нижнему регистру
        t1 = [t.lower() for t in tokens1]
        t2 = [t.lower() for t in tokens2]

        # Для честного сравнения нормализуем 'ё' -> 'е'
        t1_norm = [t.replace('ё', 'е') for t in t1]
        t2_norm = [t.replace('ё', 'е') for t in t2]

        #debug_string_character_codes(t1_norm)
        #debug_string_character_codes(t2_norm)

        # 1. Проверка Фамилии (индекс 0)
        if t1_norm[0] != t2_norm[0]:
            return 0

        # 2. ПРОВЕРКА НА ПОЛНОЕ СОВПАДЕНИЕ
        # Если списки токенов абсолютно одинаковы по длине и составу слов
        if t1_norm == t2_norm:
            return 1

        # 3. ПРОВЕРКА НА ПОДОБИЕ (Инициалы / Разная длина ФИО)
        def are_tokens_compatible(tok1: str, tok2: str) -> bool:
            if len(tok1) == 1 or len(tok2) == 1:
                return tok1.startswith(tok2) or tok2.startswith(tok1)
            return tok1 == tok2

        # Проверяем Имя (индекс 1)
        if len(t1_norm) > 1 and len(t2_norm) > 1:
            if not are_tokens_compatible(t1_norm[1], t2_norm[1]):
                return 0
        elif len(t1_norm) != len(t2_norm):
            return 0

        # Проверяем Отчество (индекс 2)
        if len(t1_norm) > 2 and len(t2_norm) > 2:
            if not are_tokens_compatible(t1_norm[2], t2_norm[2]):
                return 0

        # Если дошли сюда, значит имена не равны, но совместимы (например, Сергей и С.)
        return 2


    def _has_same_series(self, other_author: 'Author') -> bool:
        """
        Приватный метод для проверки контекста по сериям.
        Использует нечеткое сравнение серий на основе token_set_ratio.
        """
        # Фильтруем только реальные, не пустые серии у обоих авторов
        my_real_series = [s.name for s in self.series_list if not s.is_virtual and s.name.strip()]
        other_real_series = [s.name for s in other_author.series_list if not s.is_virtual and s.name.strip()]

        # Если у кого-то из авторов вообще нет серий, сравнивать нечего
        if not my_real_series or not other_real_series:
            return False

        # Попарно сравниваем каждую серию текущего автора с сериями второго автора
        for my_s in my_real_series:
            for other_s in other_real_series:
                if self._is_same_series(my_s, other_s):
                    # Как только нашли хотя бы одно нечеткое совпадение,
                    # гипотеза подтверждена — это один автор
                    return True

        return False



    def _has_same_book(self, other_author: 'Author') -> bool:
        """
        Приватный метод для проверки контекста по названиям книг.
        Возвращает True, если у обоих авторов совпадает хотя бы одно
        название книги (book.title), независимо от имени файла на диске.
        """
        # Собираем очищенные названия всех книг текущего автора
        my_books = set()
        for series in self.series_list:
            for book in series.books:
                if book.title:
                    my_books.add(book.title.lower().strip())

        # Собираем очищенные названия всех книг второго автора
        other_books = set()
        for series in other_author.series_list:
            for book in series.books:
                if book.title:
                    other_books.add(book.title.lower().strip())

        # Если у кого-то из авторов список книг пуст, совпадений быть не может
        if not my_books or not other_books:
            return False

        # Находим пересечение множеств названий книг
        common_books = my_books.intersection(other_books)

        # Вернет True, если найдена хотя бы одна одинаковая книга
        return len(common_books) > 0

    def _compare_author_name(self, other_author: 'Author') -> int:
        """
        Сравнивает полноту имен двух авторов по количеству значащих символов в ФИО.
        При равенстве длин приоритет ВСЕГДА отдается имени, содержащему букву 'ё'.

        Возвращает:
        1 — если имя текущего автора (self) более полное или содержит 'ё'.
        2 — если имя второго автора (other_author) более полное или содержит 'ё'.
        """
        # Разбиваем имена на токены, очищая от точек и пробелов
        tokens_self = [t.lower() for t in re.split(r'[.\s]+', self.name.strip()) if t]
        tokens_other = [t.lower() for t in re.split(r'[.\s]+', other_author.name.strip()) if t]

        # Для честного подсчета длины временно заменяем 'ё' на 'е'
        # (чтобы 'горбачев' и 'горбачёв' имели абсолютно одинаковый вес по длине)
        letters_self_count = sum(len(t.replace('ё', 'е')) for t in tokens_self)
        letters_other_count = sum(len(t.replace('ё', 'е')) for t in tokens_other)

        # Сценарий 1: Одно имя объективно длиннее другого (например, Имя против Инициала)
        if letters_self_count > letters_other_count:
            return 1
        if letters_other_count > letters_self_count:
            return 2

        # Сценарий 2: Длины имен эквивалентны (например, 'Горбачев' и 'Горбачёв')
        # Проверяем наличие буквы 'ё' в исходных именах (без учета регистра)
        has_yo_self = 'ё' in self.name.lower()
        has_yo_other = 'ё' in other_author.name.lower()

        # Если 'ё' есть у второго автора, а у текущего нет — приоритет второму
        if has_yo_other and not has_yo_self:
            return 2

        # Во всех остальных случаях (ё есть у текущего, ё нет у обоих, или ё есть у обоих)
        # приоритет остается за текущим автором
        return 1

    def _is_same_series(self, series_name1: str, series_name2: str) -> bool:
        """
        Приватный метод для нечеткого сравнения двух названий серий.
        Использует алгоритм token_set_ratio. Порог отсечения (compare_ratio)
        берется из конфигурации СУБД/TOML через родительскую библиотеку.
        """
        # Импортируем rapidfuzz локально, чтобы не перегружать глобальный импорт
        from rapidfuzz import fuzz

        # Очищаем строки от кавычек, приводим к нижнему регистру и убираем лишние пробелы
        s1 = series_name1.replace("'", "").replace('"', "").lower().strip()
        s2 = series_name2.replace("'", "").replace('"', "").lower().strip()

        # Если одна из строк после очистки оказалась пустой, совпадение невозможно
        if not s1 or not s2:
            return False

        # Извлекаем порог совпадения из конфигурации.
        # Так как Author не хранит конфиг напрямую, мы безопасно запрашиваем его.
        # Если путь к конфигу недоступен, используем жесткий эталон 81, как в вашем TOML.

        series_cfg = getattr(self, 'config', {}).get("series", {})
        if not series_cfg and hasattr(self, 'library') and self.library:
            series_cfg = self.library.config.get("series", {})

        threshold = series_cfg.get("compare_ratio", 81)

        # Вычисляем коэффициент схожести по множествам слов
        ratio = fuzz.token_set_ratio(s1, s2)

        # Возвращаем True, если схожесть строк выше или равна порогу
        return ratio >= threshold

    def is_same_as(self, other_author: 'Author', config: dict) -> bool:
        """
        Главный публичный метод сопоставления авторов.
        Реализует каскадный фильтр:
        1. Сверяет фамилию (с заменой е/ё). Разные фамилии -> False.
        2. Проверяет полное совпадение токенов ФИО. Полное равенство -> True.
        3. Если ФИО только похожи (инициалы), делегирует проверку контекста сериям.
        """
        tokens1 = re.split(r'[.\s]+', self.name.strip())
        tokens2 = re.split(r'[.\s]+', other_author.name.strip())

        # Фильтруем пустые элементы
        t1 = [t.lower() for t in tokens1 if t]
        t2 = [t.lower() for t in tokens2 if t]

        if not t1 or not t2:
            return False

        # Для честного сравнения нормализуем 'ё' -> 'е' (русские буквы, код 1077)
        t1_norm = [t.replace('ё', 'е') for t in t1]
        t2_norm = [t.replace('ё', 'е') for t in t2]

        # 1. Проверка Фамилии (индекс 0)
        if t1_norm[0] != t2_norm[0]:
            return False

        # 2. ПРОВЕРКА НА ПОЛНОЕ СОВПАДЕНИЕ ФИО
        if t1_norm == t2_norm:
            return True

        # 3. ПРОВЕРКА НА СОВМЕСТИМОСТЬ (Инициалы / Разная длина ФИО)
        def are_tokens_compatible(tok1: str, tok2: str) -> bool:
            if len(tok1) == 1 or len(tok2) == 1:
                return tok1.startswith(tok2) or tok2.startswith(tok1)
            return tok1 == tok2

        # Проверяем Имя (индекс 1)
        if len(t1_norm) > 1 and len(t2_norm) > 1:
            if not are_tokens_compatible(t1_norm[1], t2_norm[1]):
                return False
        elif len(t1_norm) != len(t2_norm):
            return False

        # Проверяем Отчество (индекс 2)
        if len(t1_norm) > 2 and len(t2_norm) > 2:
            if not are_tokens_compatible(t1_norm[2], t2_norm[2]):
                return False

        # --- ГРАММАТИЧЕСКАЯ СОВМЕСТИМОСТЬ ДОКАЗАНА (Имена похожи) ---
        # Теперь запускаем Шаг 2 и Шаг 3 контекстной проверки.
        # Опрашиваем наши серии, делегируя им сопоставление внутренних книг и названий серий.
        for my_series in self.series_list:
            # Виртуальные серии пропускаем, их контекст проверится на уровне книг
            if my_series.is_virtual:
                continue
            for other_series in other_author.series_list:
                if other_series.is_virtual:
                    continue

                # Вызываем чистый метод класса Series
                if my_series.is_same_as(other_series, config):
                    return True

        # Если реальные серии не пересеклись, проверяем одиночные книги из виртуальных серий
        my_virtual = next((s for s in self.series_list if s.is_virtual), None)
        other_virtual = next((s for s in other_author.series_list if s.is_virtual), None)

        if my_virtual and other_virtual:
            # Если у обоих авторов есть книги без серий, проверяем их совпадение
            for my_book in my_virtual.books:
                for other_book in other_virtual.books:
                    if my_book.is_same_as(other_book):
                        return True

        return False
