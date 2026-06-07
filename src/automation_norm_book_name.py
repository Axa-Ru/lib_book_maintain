import logging
from pathlib import Path
from typing import List, Dict, Any, Optional


def automation_norm_book_name(
        authors: List[Any],
        book_cfg: Any,
        lang: str = "ru",
        stats: Optional[Dict[str, Any]] = None
) -> int:
    """
    [Версия 0.9.5] Нормализация имен файлов книг на диске.
    Рассчитывает идеальное имя файла и безопасно переименовывает его.
    Защищен от FileNotFoundError (после Шага 3) и FileExistsError (дуэлью размеров).

    :param authors: Список объектов авторов для обработки.
    :param book_cfg: Конфигурация форматирования имен книг.
    :param lang: Базовый язык для нормализации.
    :param stats: Словарь для накопления глобальной статистики изменений.
    :return: Количество успешно нормализованных файлов за текущий проход.
    """
    if stats is None:
        stats = {"normalized_books": 0}

    local_normalized_count = 0

    for author in authors:
        if not hasattr(author, 'series') or not author.series:
            continue

        for series in author.series.values():
            # Проверяем, есть ли книги в серии
            if not hasattr(series, 'books') or not series.books:
                continue

            # Определяем текущую директорию серии на диске
            # Если книг нет, папка вычисляется по имени серии
            if len(series.books) > 0:
                current_dir = series.books[0].path.parent
            else:
                author_folder = Path(author.folder_path) if hasattr(author, 'folder_path') else Path(author.path)
                current_dir = author_folder / series.name

            if not current_dir.exists():
                continue

            # Обходим копию списка книг, чтобы безопасно удалять элементы в процессе дуэли
            for book in list(series.books):

                # 🔥 ФИКС 1: Защита от изменений на Шаге 3 (если книга перемещена/удалена ранее)
                if not book.path.exists():
                    if book in series.books:
                        series.books.remove(book)
                    continue

                # Рассчитываем идеальное целевое имя файла (new_name)
                book.compute_new_name(author.name, book_cfg, base_lang=lang)

                old_path = book.path
                new_path = current_dir / book.new_name

                # Если имя файла на диске отличается от вычисленного идеала
                if old_path.name != book.new_name:

                    # 🔥 ФИКС 2: Защита от перезаписи. Если файл с новым именем УЖЕ существует
                    if new_path.is_file():
                        # Запускаем дуэль размеров (1 - текущий лучше, 2 или 0 - на диске лучше/равен)
                        result = book.compare_with(new_path)

                        if result == 1:
                            # Текущий файл (old_path) лучше -> удаляем тот, что на диске, освобождая место
                            try:
                                new_path.unlink(missing_ok=True)
                            except Exception as e:
                                logging.error(f"Не удалось удалить старый дубликат {new_path.name}: {e}")
                                continue
                        else:
                            # Файл на диске лучше или равен -> текущую плохую копию просто удаляем
                            try:
                                old_path.unlink(missing_ok=True)
                                if book in series.books:
                                    series.books.remove(book)
                            except Exception as e:
                                logging.error(f"Не удалось удалить худший дубликат {old_path.name}: {e}")
                            continue  # Переходим к следующей книге

                    # Если путь свободен или мы его очистили — безопасно переименовываем
                    try:
                        old_path.rename(new_path)
                        book.path = new_path  # Синхронизируем путь в объекте памяти
                        local_normalized_count += 1
                        stats["normalized_books"] += 1
                        logging.info(f"  Файл переименован: '{old_path.name}' ──> '{book.new_name}'")
                    except Exception as e:
                        logging.error(f"Ошибка при переименовании файла {old_path.name} в {book.new_name}: {e}")

    return local_normalized_count
