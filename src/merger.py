import os
import shutil
import logging
from pathlib import Path
from library_class import Library


def merge_libraries(main_lib: Library, candidate_lib: Library):
    """
    Переносит все книги из библиотеки candidate_lib в библиотеку main_lib.
    Обе библиотеки должны быть предварительно нормализованы.
    """
    logging.info(f"=== Слияние библиотек: {candidate_lib.base_path} ──> {main_lib.base_path} ===")

    # Перед началом работы убедимся, что обе структуры актуальны в памяти
    main_lib.scan()
    candidate_lib.scan()

    # Обходим структуру кандидата по языкам и буквам
    for lang, letters in candidate_lib.catalog.items():
        for letter, authors in letters.items():
            for candidate_author in authors:

                # Ищем точно такого же автора в основной библиотеке (в том же языке и букве)
                main_author = None
                if lang in main_lib.catalog and letter in main_lib.catalog[lang]:
                    for auth in main_lib.catalog[lang][letter]:
                        if auth.name.lower().strip() == candidate_author.name.lower().strip():
                            main_author = auth
                            break

                # СЛУЧАЙ 1: Автор уже существует в основной библиотеке
                if main_author:
                    logging.info(f"  [Слияние] Автор '{candidate_author.name}' найден в основной базе. Перенос книг...")
                    # Используем ваш встроенный ООП метод для переноса файлов и удаления папки
                    candidate_author.join_with(main_author)

                # СЛУЧАЙ 2: Автора еще нет в основной библиотеке
                else:
                    logging.info(f"  [Перенос] Автор '{candidate_author.name}' новый. Перемещение каталога целиком...")

                    # Формируем целевой путь для папки автора в основной библиотеке
                    target_letter_dir = main_lib.base_path / lang / letter

                    # Создаем папки языка и буквы, если их не было
                    target_letter_dir.mkdir(parents=True, exist_ok=True)

                    target_author_dir = target_letter_dir / candidate_author.name

                    try:
                        # Перемещаем всю папку автора со всем содержимым
                        shutil.move(str(candidate_author.folder_path), str(target_author_dir))
                    except Exception as e:
                        logging.error(f"  Не удалось переместить каталог автора {candidate_author.name}: {e}")

    # Финальная очистка: удаляем пустые папки букв и языков в кандидате, если они остались
    _cleanup_empty_dirs(candidate_lib.base_path)

    # Обновляем состояние основной библиотеки в памяти
    main_lib.scan()
    logging.info(f"=== Слияние библиотек завершено. Текущее количество книг в основной базе: {len(main_lib.get_all_books())} ===\n")


def _cleanup_empty_dirs(root_path: Path):
    """Рекурсивно удаляет пустые директории в исходном каталоге кандидата."""
    if not root_path.exists():
        return

    # Обходим папки снизу вверх (сначала самые глубокие)
    for dirpath, dirnames, filenames in os.walk(root_path, topdown=False):
        current_dir = Path(dirpath)
        # Пропускаем сам корень библиотеки-кандидата
        if current_dir == root_path:
            continue
        try:
            # Пытаемся удалить. Метод rmdir() упадет с OSError, если папка не пуста
            current_dir.rmdir()
        except OSError:
            pass
