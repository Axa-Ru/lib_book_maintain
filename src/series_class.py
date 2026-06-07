# -------------------------------------------------------------
# module: src/series_class.py
# -------------------------------------------------------------

import logging
from pathlib import Path
from utils import sanitize_text_base


class Series:
    """Класс, описывающий серию книг.
    Если имя серии пустое (""), объект считается виртуальной серией для одиночных книг.
    """

    def __init__(self, name: str = ""):
        # self.name хранит строго точное физическое имя папки с диска "как есть"
        self.name = name

        # Поле целевого состояния: идеальное имя серии (по умолчанию такое же)
        self.new_name = name

        self.books = []
        self._is_virtual = (name == "")

    @property
    def is_virtual(self) -> bool:
        """Показывает, является ли серия заглушкой для одиночных книг."""
        return self._is_virtual

    def sanitize_name(self, replaces: dict) -> str:
        """
        Базовая очистка названия серии от подстрок-мусора на основе словаря конфигурации.
        """
        if not self.name or self.is_virtual:
            return ""

        result_name = self.name
        # Применяем текстовые замены подстрок из TOML-конфигурации
        for old_value, new_value in replaces.items():
            if old_value.lower() in result_name.lower():
                import re
                result_name = re.sub(re.escape(old_value), new_value, result_name, flags=re.IGNORECASE)

        return result_name.strip()

    def compute_new_name(self, replaces: dict, author_name: str, base_lang: str = "ru"):
        """
        [Версия 0.9.3] Вычисляет идеальное имя серии, инкапсулируя все правила очистки.
        Результат фиксируется во внутреннем поле целевого состояния self.new_name.
        """
        from utils import fix_uppercase_text, strip_spaces_inside_brackets, remove_author_name_from_text

          # 1 Сначала делаем базовые текстовые замены из TOML
        res = self.sanitize_name(replaces)

        # 2 Выполняем нормализацию и схлопывание пробелов
        res = sanitize_text_base(res, base_lang=base_lang)

        # 3 чистим скобки
        res = strip_spaces_inside_brackets(res)

        # 4 Вырезаем дубликат имени автора из названия серии
        res = remove_author_name_from_text(res, author_name)

        # 5 Переводим в правильный регистр (первая заглавная)
        res = fix_uppercase_text(res)

        # Фиксируем идеальное имя
        self.new_name = res

    def _check_name_similarity(self, other_name: str, config: dict) -> bool:
        """Внутренний метод для нечеткого сравнения названий серий."""
        from rapidfuzz import fuzz

        s1 = self.new_name.replace("'", "").replace('"', "").lower().strip()
        s2 = other_name.replace("'", "").replace('"', "").lower().strip()

        if s1 == s2:
            return True

        # Извлекаем порог совпадения серий из конфигурации TOML
        series_cfg = config.get("series", {})
        threshold = series_cfg.get("compare_ratio", 81)

        # Вычисляем коэффициент схожести по множествам слов
        ratio = fuzz.token_set_ratio(s1, s2)
        return ratio >= threshold

    def _check_books_match(self, other_series: 'Series') -> bool:
        """Внутренний метод проверки контекста книг между двумя сериями."""
        for my_book in self.books:
            for other_book in other_series.books:
                if my_book.is_same_as(other_book):
                    return True
        return False

    def is_same_as(self, other_series: 'Series', config: dict) -> bool:
        """Главный публичный метод сопоставления серий (Имена -> Контекст книг)."""
        # 1. Проверяем схожесть вычисленных названий серий
        if self._check_name_similarity(other_series.new_name, config):
            return True

        # 2. Если имена не похожи, проверяем пересечение по книгам внутри серий
        if self._check_books_match(other_series):
            return True

        return False

    def join_with(self, other_series: 'Series', target_author_folder: Path) -> bool:
        """
        [Версия 0.9.5] Физически поглощает текущую серию другой серией.
        target_author_folder — это папка ГЛАВНОГО автора, куда перемещаются книги.
        """
        import shutil

        # 🔥 ИСПРАВЛЕНО: Если это виртуальная серия (слияние одиночных книг в корнях)
        if self.is_virtual:
            # Для виртуальной серии исходный и целевой каталоги — это сами корни авторов.
            # Нам нужно понять, где корень исходного автора. Мы берем его из пути первой книги.
            if self.books and len(self.books) > 0:
                source_dir = self.books[0].path.parent
            else:
                return True  # Если книг в корне нет, перенос не требуется
            target_dir = target_author_folder
        else:
            # 🔥 ИСПРАВЛЕНО: Для реальной серии мы определяем её исходный путь на диске
            # строго по её книгам, чтобы гарантированно не перепутать папки авторов!
            if self.books and len(self.books) > 0:
                source_dir = self.books[0].path.parent
            else:
                # Если книг в памяти нет, но папка физически существует на диске — удаляем её,
                # чтобы она не вызывала повторное зацикливание конвейера на Шаге 3.
                fallback_source = target_author_folder / self.name
                if fallback_source.exists() and fallback_source.is_dir():
                    try:
                        fallback_source.rmdir()
                    except OSError:
                        pass
                return True

            target_dir = target_author_folder / other_series.name

        # 🔥 ИСПРАВЛЕНО: Если целевой папки серии на диске нет, её нужно создать.
        # Иначе метод вернет False, логирование пропустится, и начнется бесконечный цикл.
        if not target_dir.exists():
            try:
                target_dir.mkdir(parents=True, exist_ok=True)
            except Exception:
                return False

        if not source_dir.exists():
            return False

        # Обходим копию списка книг текущей серии
        for my_book in list(self.books):
            target_book_path = target_dir / my_book.path.name

            # Сценарий 1: Такой книги в целевой серии еще нет — просто перемещаем
            if not target_book_path.is_file():
                try:
                    shutil.move(str(my_book.path), str(target_dir))
                    my_book.path = target_book_path  # Синхронизируем путь в памяти
                    other_series.books.append(my_book)
                except Exception:
                    return False
                continue

            # Сценарий 2: Книга уже существует — запускаем защиту дубликатов по размеру
            result = my_book.compare_with(target_book_path)

            if result == 1:
                # Текущий файл больше/лучше — удаляем старый, перемещаем новый
                target_book_path.unlink(missing_ok=True)
                try:
                    shutil.move(str(my_book.path), str(target_dir))
                    my_book.path = target_book_path
                    other_series.books.append(my_book)
                except Exception:
                    return False
            elif result == 2 or result == 0:
                # На диске файл лучше или равен — текущую копию просто удаляем с диска
                my_book.path.unlink(missing_ok=True)

        # После переноса всех файлов удаляем пустую исходную папку серии на диске (если она реальная)
        if not self.is_virtual:
            try:
                source_dir.rmdir()
                return True
            except OSError:
                return False

        return True

