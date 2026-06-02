from pathlib import Path
import re
from series_class import Series
from utils import apply_title_replacements


class Book:
    """Класс, описывающий отдельную книгу."""
    def __init__(self, file_path: Path, series: Series):
        self.path = file_path
        self.size = file_path.stat().st_size if file_path.exists() else 0
        self.series = series  # Книга ВСЕГДА привязана к объекту серии
        self.author = ""
        self.title = ""
        self.separator = ""

    def sanitize_name(self, book_config: dict) -> str:
        """Реализация ТЗ очистки имени файла книги."""
        book_name = self.path.stem  # Работаем с именем файла без расширения .epub

        # 1. Отделить от названия фамилию автора и разделитель ("-" | "%d")
        match = re.match(r"^([^\d\-]+?)\s*(-|\d+)\s*(.*)$", book_name.strip())

        if not match:
            return book_name

        author_raw = match.group(1).strip()
        separator_raw = match.group(2)
        title_raw = match.group(3).strip()

        # [НОВЫЙ ШАГ]: Если в конфиге включен title_change, делаем замены в названии книги
        # Импортируем функцию из utils: from src.utils import apply_title_replacements
        if book_config.get("title_change", False):
            replacements = book_config.get("title_substr", [])
            title_raw = apply_title_replacements(title_raw, replacements)

        # 2. Перевести раскладку фамилии автора: Первая заглавная, остальные строчные
        self.author = author_raw.lower().capitalize()

        # 3. Привести разделитель в вид %02d
        if separator_raw.isdigit():
            self.separator = f"{int(separator_raw):02d}"
        else:
            self.separator = "-"

        # 4. Вызвать очистку названия через метод серии
        # (Передаем тот же словарь замен, так как в комментарии TOML указано "в title и series")
        temp_series = Series(title_raw)

        series_replaces = dict(book_config.get("title_substr", [])) if book_config.get("title_change", False) else {}
        sanitized_book_name = temp_series.sanitize_name(series_replaces)

        # 5. Если (len(title) - len(series) > limit) то удаляем из названия подстроку series_name
        min_name_limit = book_config.get("title_min_limit", 8)
        if not self.series.is_virtual and (len(sanitized_book_name) - len(self.series.name) > min_name_limit):
            sanitized_book_name = re.sub(re.escape(self.series.name), '', sanitized_book_name, flags=re.IGNORECASE)

            # Очистка возможных артефактов после удаления подстроки
            sanitized_book_name = re.sub(r'\s*-\s*', '-', sanitized_book_name)
            sanitized_book_name = re.sub(r'\s+', ' ', sanitized_book_name)
            sanitized_book_name = re.sub(r'\.+$', '', sanitized_book_name)
            sanitized_book_name = sanitized_book_name.strip()

            if sanitized_book_name:
                sanitized_book_name = sanitized_book_name[0].upper() + sanitized_book_name[1:]

        self.title = sanitized_book_name

        # 6-7. Собрать и вернуть полное название книги
        return f"{self.author} {self.separator} {self.title}"

    @staticmethod
    def get_resolved_name(book_name1: str, book_name2: str) -> str:
        """Реализация функции get_book_name (выбор строки с буквой 'ё')."""
        if 'ё' in book_name1.lower():
            return book_name1
        return book_name2


    def compare_with(self, other_book_path: Path) -> int:
        """Реализация функции compare_book_title (сравнение с другим файлом по имени и размеру)."""
        b1p = self.path.name
        b2p = self.path.parent.name
        if self.path.name == other_book_path.name:
            if self.size > other_book_path.stat().st_size:
                return 1
            return 2
        return 0


    def is_same_as(self, other_book: 'Book') -> bool:
        """
        Проверяет, является ли текущая книга тем же произведением,
        что и другая книга, на основе сравнения их очищенных названий.
        Алгоритм полностью сохранен из прошлых успешных тестов контекста.
        """
        # Если у какой-то из книг нет названия (оно пустое), совпадение невозможно
        if not self.title or not other_book.title:
            return False

        # Сравниваем названия произведений, как мы это делали ранее
        return self.title.lower().strip() == other_book.title.lower().strip()
