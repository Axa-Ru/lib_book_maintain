from typing import Dict, List
import re
from pathlib import Path
from utils import capitalize_first_letters


class Series:
    """Класс, описывающий серию книг.
    Если имя серии пустое (""), объект считается виртуальной серией для одиночных книг.
    """
    def __init__(self, name: str = ""):
        self.name = name.strip()
        self.books: List['Book'] = []

    @property
    def is_virtual(self) -> bool:
        """Показывает, является ли серия заглушкой для одиночных книг."""
        return self.name == ""

    def sanitize_name(self, replaces: Dict[str, str]) -> str:
        """Реализация ТЗ очистки названия серии (бывшая функция sanitize_series_name)."""
        name = self.name

        # 1. Замены подстрок из словаря replaces
        for old_value, new_value in replaces.items():
            name = name.replace(old_value, new_value)

        # 2. Убрать знаки препинания ",?:"
        name = re.sub(r'[,?:]', '', name)

        # 3. Если есть пробел между точками, удалить его
        while True:
            new_name = re.sub(r'\.\s+\.', '..', name)
            if new_name == name:
                break
            name = new_name

        # 4. Внутри названия убрать дублирующие точки, заменив их одной
        name = re.sub(r'\.{2,}', '.', name)

        # 5. Если между словами есть дефис, убрать пробелы вокруг дефиса
        name = re.sub(r'\s*-\s*', '-', name)

        # 6. Убрать лидирующие, концевые и дублирующие пробелы
        name = re.sub(r'\s+', ' ', name)
        name = name.strip()

        # 7. Если в конце названия есть точки, убрать их
        name = re.sub(r'\.+$', '', name)
        name = name.strip()

        if not name:
            return ""

        # 8. Перевести раскладку в соответствии с правилами русского языка
        name = capitalize_first_letters(name)

        # Обновляем имя внутри объекта после очистки
        self.name = name
        return name

    def join_with(self, other_series: 'Series', author_folder: Path) -> bool:
        """
        Поглощает текущую серию (self) другой серией (other_series).
        Переносит уникальные книги, разрешает конфликты дубликатов по размеру
        и удаляет пустую исходную папку текущей серии.
        """
        import shutil

        source_dir = author_folder / self.name
        target_dir = author_folder / other_series.name

        if not source_dir.exists() or not target_dir.exists():
            return False

        # Обходим все книги текущей (поглощаемой) серии
        for my_book in list(self.books):
            target_book_path = target_dir / my_book.path.name

            # Сценарий 1: Такой книги в целевой серии еще нет — просто перемещаем
            if not target_book_path.is_file():
                try:
                    shutil.move(str(my_book.path), str(target_dir))
                    other_series.books.append(my_book)
                except Exception:
                    return False
                continue

            # Сценарий 2: Книга уже существует — запускаем защиту дубликатов по размеру
            result = my_book.compare_with(target_book_path)

            if result == 1:
                # Текущий файл больше/лучше — удаляем старый, перемещаем новый
                target_book_path.unlink()
                shutil.move(str(my_book.path), str(target_dir))
            elif result == 2 or result == 0:
                # На диске файл лучше или равен — текущий просто удаляем
                my_book.path.unlink()

        # После переноса всех книг удаляем пустую исходную папку серии
        try:
            source_dir.rmdir()
            return True
        except OSError:
            return False

    def _has_same_book(self, other_series: 'Series') -> bool:
        """
        Приватный метод для проверки контекста книг между двумя сериями.
        Возвращает True, если в обеих сериях совпадает хотя бы одно
        название произведения (book.title), независимо от имени файла.
        """
        my_books = {b.title.lower().strip() for b in self.books if b.title}
        other_books = {b.title.lower().strip() for b in other_series.books if b.title}

        if not my_books or not other_books:
            return False

        # Находим пересечение (общие книги)
        common_books = my_books.intersection(other_books)
        return len(common_books) > 0


    def _check_name_similarity(self, other_name: str, config: dict) -> bool:
        """
        Внутренний метод для нечеткого сравнения названий серий.
        Полностью сохраняет отлаженный алгоритм token_set_ratio.
        """
        from rapidfuzz import fuzz

        # Наша стандартная очистка строк от кавычек и пробелов
        s1 = self.name.replace("'", "").replace('"', "").lower().strip()
        s2 = other_name.replace("'", "").replace('"', "").lower().strip()

        if s1 == s2:
            return True

        # Извлекаем порог совпадения из секции [series] конфигурации TOML
        series_cfg = config.get("series", {})
        threshold = series_cfg.get("compare_ratio", 81)

        # Вычисляем коэффициент схожести по множествам слов
        ratio = fuzz.token_set_ratio(s1, s2)
        return ratio >= threshold


    def _check_books_match(self, other_series: 'Series') -> bool:
        """
        Внутренний метод проверки контекста книг между двумя сериями.
        Делегирует сравнение объектам класса Book.
        """
        # Попарно сравниваем каждую книгу текущей серии с книгами другой серии
        for my_book in self.books:
            for other_book in other_series.books:
                # Используем чистый метод класса Book
                if my_book.is_same_as(other_book):
                    return True
        return False


    def is_same_as(self, other_series: 'Series', config: dict) -> bool:
        """
        Главный публичный метод сопоставления серий.
        Реализует каскадный фильтр: сначала проверяет имя,
        если имена разные — заглядывает внутрь и проверяет книги.
        """
        # 1. Сначала проверяем схожесть названий серий
        if self._check_name_similarity(other_series.name, config):
            return True

        # 2. Если имена не похожи, проверяем книги внутри серий
        if self._check_books_match(other_series):
            return True

        return False
