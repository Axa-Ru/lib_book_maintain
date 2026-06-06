# -------------------------------------------------------------
# module: src/automation_dedup_books.py
# -------------------------------------------------------------

import logging
from library_class import Library


def automation_dedup_books(library: 'Library', stats: dict):
    """
    Кросс-серийная дедупликация книг.
    Находит дубликаты произведений между корнем автора (одиночки) и его реальными сериями.
    Разрешает конфликты по размеру файлов и учитывает их в глобальной статистике stats.
    :param library:
    :param stats:
    :return:
    """
    logging.info("Шаг 4.5: Кросс-серийное схлопывание дубликатов книг (Корень <──> Подпапки)...")

    for lang, letters in library.catalog.items():
        for letter, authors in letters.items():
            for author in authors:

                # Находим виртуальную серию автора (его корень)
                virtual_series = next((s for s in author.series_list if s.is_virtual), None)
                if not virtual_series or not virtual_series.books:
                    continue  # Если в корнях у автора пусто — идем дальше

                # Обходим копию списка одиночных книг в корне
                for my_book in list(virtual_series.books):
                    duplicate_found = False

                    # Ищем эту книгу во всех реальных сериях автора
                    for real_series in author.series_list:
                        if real_series.is_virtual:
                            continue

                        for other_book in list(real_series.books):
                            # ООП-сравнение чистых заголовков без учета номеров серий
                            if my_book.is_same_as(other_book):

                                # Определяем точный физический путь серийной книги на диске
                                target_book_path = other_book.path

                                # Запускаем дуэль размеров
                                res = my_book.compare_with(target_book_path)

                                if res == 1:
                                    # Книга в корне БОЛЬШЕ -> заменяем ею меньший файл внутри папки серии
                                    target_book_path.unlink(missing_ok=True)
                                    try:
                                        import shutil
                                        shutil.move(str(my_book.path), str(target_book_path))

                                        # Синхронизируем метаданные в памяти для оставшегося объекта
                                        other_book.path = target_book_path
                                        other_book.name = my_book.name

                                        # Удаляем одиночку из памяти корня
                                        virtual_series.books.remove(my_book)
                                        if stats: stats["deleted_books"] += 1
                                        logging.info(
                                            f"  [Кросс-дедупликация] Книга из корня перемещена в серию: '{my_book.name}'")
                                    except Exception as e:
                                        logging.error(f"  Не удалось заменить серийный файл книгой из корня: {e}")

                                    duplicate_found = True
                                    break

                                elif res == 2 or res == 0:
                                    # Книга в серии БОЛЬШЕ или равна -> одиночку из корня просто выкидываем
                                    my_book.path.unlink(missing_ok=True)
                                    virtual_series.books.remove(my_book)
                                    if stats: stats["deleted_books"] += 1
                                    logging.info(
                                        f"  [Кросс-дедупликация] Удален худший дубликат из корня автора: '{my_book.name}'")

                                    duplicate_found = True
                                    break

                        if duplicate_found:
                            break

