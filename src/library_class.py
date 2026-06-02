import os
import logging
from pathlib import Path
from typing import Dict, List, Optional
from author_class import Author
from book_class import Book


class Library:
    """Класс верхнего уровня для управления всей библиотекой книг."""

    def __init__(self, config: dict):
        self.config = config
        self.base_path = self._get_base_path()

        # Индекс структуры: { "Ru": { "А": [Author, Author], "Б": [...] }, "En": {...} }
        self.catalog: Dict[str, Dict[str, List[Author]]] = {}


    def _get_base_path(self) -> Path:
        """Определяет корневой путь библиотеки на основе флага тестирования."""
        paths_cfg = self.config.get("paths", {})
        if paths_cfg.get("use_test", False):
            return Path(paths_cfg.get("src_test_base", "/tmp/test_lib/"))

        # Если не тест, берем из отформатированной секции directories
        dirs_cfg = self.config.get("directories", {})
        return Path(dirs_cfg.get("src_base", ""))


    def scan(self):
        """
        Сканирует корневую директорию библиотеки и сразу заполняет
        метаданные книг (title, author, separator) при чтении с диска.
        """
        self.catalog.clear()

        if not self.base_path.exists() or not self.base_path.is_dir():
            logging.error(f"Корневой каталог библиотеки не найден: {self.base_path}")
            return

        # Извлекаем конфигурацию для книг, необходимую для метода sanitize_name
        book_cfg = self.config.get("book", {})

        for lang_dir in self.base_path.iterdir():
            if not lang_dir.is_dir() or lang_dir.name.startswith('.'):
                continue

            lang = lang_dir.name
            self.catalog[lang] = {}

            for letter_dir in lang_dir.iterdir():
                if not letter_dir.is_dir() or letter_dir.name.startswith('.'):
                    continue

                letter = letter_dir.name
                self.catalog[lang][letter] = []

                for author_dir in letter_dir.iterdir():
                    if not author_dir.is_dir() or author_dir.name.startswith('.'):
                        continue

                    # Передаем конфигурацию автора, если ваш конструктор это поддерживает,
                    # либо просто создаем объект
                    author = Author(folder_path=author_dir)

                    # 🔥 Передаем book_cfg внутрь сканера автора, чтобы книги наводящегося автора тоже парсились
                    if hasattr(author, 'scan_contents'):
                        # Изменяем вызов сканирования контента автора, передавая настройки книг
                        author.scan_contents(book_cfg)
                    else:
                        author.scan_contents()

                    self.catalog[lang][letter].append(author)


    def find_author(self, author_name: str) -> List[Author]:
        """Поиск автора по всей библиотеке (имени его папки)."""
        found_authors = []
        for lang, letters in self.catalog.items():
            for letter, authors in letters.items():
                for author in authors:
                    if author_name.lower() in author.name.lower():
                        found_authors.append(author)
        return found_authors


    def get_all_books(self) -> List[Book]:
        """Возвращает плоский список абсолютно всех книг в библиотеке."""
        all_books = []
        for lang, letters in self.catalog.items():
            for letter, authors in letters.items():
                for author in authors:
                    for series in author.series_list:
                        all_books.extend(series.books)
        return all_books


    def run_deduplication(self):
        """
        Запуск логики дедупликации авторов на основе конфига.
        Если один и тот же автор разбросан по разным папкам (например, опечатка
        или разная раскладка), метод подготавливает их к объединению через Author.join_with.
        """
        if not self.config.get("author", {}).get("authors_deduplicate", False):
            return

        # Логику поиска дублей (сравнение ФИО Лев Толстой vs Толстой Лев)
        # и вызов author1.join_with(author2) можно внедрить сюда.
        pass


    def __repr__(self) -> str:
        langs = list(self.catalog.keys())
        return f"<Library base_path={self.base_path} languages={langs}>"
