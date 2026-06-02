#-------------------------------------------------------------
# module: src/automation_norm_book_name.py
#-------------------------------------------------------------

from library_class import Library
import logging


def automation_norm_book_name(library: 'Library', book_cfg: dict, stats: dict):
    logging.info("Шаг 4: Нормализация имен файлов книг...")
    for lang, letters in library.catalog.items():
        for letter, authors in letters.items():
            for author in authors:
                for series in author.series_list:
                    for book in series.books:
                        # Передаем словарь конфигурации книги целиком (Исправление AttributeError)
                        new_stem = book.sanitize_name(book_cfg)
                        new_filename = f"{new_stem}.epub"

                        if book.path.name != new_filename:
                            old_path = book.path
                            new_path = book.path.parent / new_filename

                            if new_path.exists():
                                res = book.compare_with(new_path)
                                if res == 1:
                                    new_path.unlink()
                                    old_path.rename(new_path)
                                    stats["deleted_books"] += 1
                                    logging.info(f"  Заменен дубликат: {new_filename} (текущий файл больше)")
                                elif res == 2:
                                    old_path.unlink()
                                    stats["deleted_books"] += 1
                                    logging.info(f"  Удален дубликат:  {old_path.name}")
                            else:
                                try:
                                    old_path.rename(new_path)
                                    book.path = new_path
                                except Exception as e:
                                    logging.error(f"  Ошибка переименования книги {old_path.name}: {e}")

    library.scan()