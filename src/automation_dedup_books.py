# -------------------------------------------------------------
# module: src/automation_dedup_books.py
# -------------------------------------------------------------

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

def automation_dedup_books(authors: List[Any], stats: Optional[Dict[str, Any]] = None) -> int:
    """
    [Версия 0.9.6] Кросс-серийное схлопывание дубликатов книг (Корень <──> Подпапки).
    Синхронизирован со списочной структурой серий author.series_list.
    """
    if stats is None:
        stats = {"deleted_books": 0} # Ключ приведен к единому стандарту оркестратора

    local_dedup_count = 0

    for author in authors:
        # 🔥 ФИКС 1: Перебор по списочной структуре серий
        if not hasattr(author, 'series_list') or not author.series_list:
            continue

        # Собираем все серии автора для перекрестного анализа
        all_series = list(author.series_list)
        seen_books: Dict[str, Any] = {}

        for series in all_series:
            if not hasattr(series, 'books') or not series.books:
                continue

            for book in list(series.books):
                # Проверяем, существует ли файл физически на диске
                if not book.path.exists():
                    if book in series.books:
                        series.books.remove(book)
                    continue

                # Формируем ключ дедупликации (идеальное имя файла без учета регистра)
                book_key = getattr(book, 'new_name', book.path.name).lower()

                # Если мы уже встречали эту книгу у этого автора в другой серии или корне
                if book_key in seen_books:
                    primary_book = seen_books[book_key]

                    # Проверяем, существует ли первый найденный файл
                    if not primary_book.path.exists():
                        seen_books[book_key] = book
                        continue

                    # Запускаем дуэль размеров между дубликатами
                    result = book.compare_with(primary_book.path)

                    if result == 1:
                        # Текущая книга лучше -> удаляем старую с диска и из её серии
                        try:
                            primary_book.path.unlink(missing_ok=True)
                            for s in all_series:
                                if primary_book in s.books:
                                    s.books.remove(primary_book)
                        except Exception as e:
                            logging.error(f"Не удалось удалить худший дубликат {primary_book.path.name}: {e}")

                        # На место главной книги ставим текущую
                        seen_books[book_key] = book
                        local_dedup_count += 1
                        stats["deleted_books"] += 1
                        logging.info(f"  [Кросс-серия] Замена дубликата лучшим файлом: {book.path.name}")

                    else:
                        # Текущая книга хуже или равна -> удаляем её, а старую оставляем
                        try:
                            book.path.unlink(missing_ok=True)
                            if book in series.books:
                                series.books.remove(book)
                        except Exception as e:
                            logging.error(f"Не удалось удалить избыточный дубликат {book.path.name}: {e}")

                        local_dedup_count += 1
                        stats["deleted_books"] += 1
                        logging.info(f"  [Кросс-серия] Удален худший/равный дубликат книги: {book.path.name}")

                else:
                    seen_books[book_key] = book

    return local_dedup_count
