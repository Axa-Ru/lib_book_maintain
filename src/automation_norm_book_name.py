# -------------------------------------------------------------
# module: src/automation_norm_book_name.py
# -------------------------------------------------------------

import logging
from library_class import Library


def automation_norm_book_name(library: 'Library', book_cfg: dict, stats: dict):
    """
    [Версия 0.9.3] Шаг 4: Нормализация имен файлов книг.
    Переименовывает файлы в их идеальное состояние СТРОГО внутри текущих папок.
    """
    logging.info("Шаг 4: Нормализация имен файлов книг...")

    for lang, letters in library.catalog.items():
        for letter, authors in letters.items():
            for author in authors:
                for series in author.series_list:
                    for book in list(series.books):

                        # 1. Объект книги сам рассчитывает своё идеальное имя
                        book.compute_new_name(author.name, book_cfg, base_lang=lang)
                        new_filename = book.new_name

                        # Целевой путь строго в текущей папке серии/корня
                        old_path = book.path

                        if series.is_virtual:
                            new_path = author.folder_path / new_filename
                        else:
                            new_path = author.folder_path / series.name / new_filename

                        # 2. Переименовываем только если имя файла изменилось
                        if old_path.name != new_filename:
                            if new_path.exists():
                                # Локальный конфликт внутри ОДНОЙ папки
                                res = book.compare_with(new_path)
                                if res == 1:
                                    new_path.unlink(missing_ok=True)
                                    old_path.rename(new_path)
                                    book.path = new_path
                                    book.name = new_filename
                                    if stats: stats["deleted_books"] += 1
                                elif res == 2 or res == 0:
                                    old_path.unlink(missing_ok=True)
                                    if book in series.books:
                                        series.books.remove(book)
                                    if stats: stats["deleted_books"] += 1
                            else:
                                try:
                                    old_path.rename(new_path)
                                    book.path = new_path
                                    book.name = new_filename
                                except Exception as e:
                                    logging.error(f"  Ошибка локального переименования книги {old_path.name}: {e}")

