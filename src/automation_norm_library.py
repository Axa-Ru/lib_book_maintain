# -------------------------------------------------------------
# module: src/automation_norm_library.py
# -------------------------------------------------------------

import logging
import shutil
from pathlib import Path
from src.library_class import Library


def automation_norm_library(library: 'Library'):
    """
    [Версия 0.9.5] Шаг 1: Нормализация имен папок авторов со слиянием.
    Если целевая кириллическая папка уже существует на диске,
    скрипт физически поглощает грязную папку, перенося её контент.
    """
    logging.info("Шаг 1: Нормализация имен авторов (с каскадным слиянием)...")

    for lang, letters in library.catalog.items():
        for letter, authors in letters.items():
            for author in authors:

                old_path = author.folder_path
                new_filename = author.new_name
                new_path = old_path.parent / new_filename

                # Если физическое имя папки на диске не совпадает с идеальным
                if old_path.name != new_filename:

                    # СЦЕНАРИЙ А: Целевой чистый каталог уже занят (латинский конфликт близнецов)
                    if new_path.exists():
                        logging.info(f"  [Конфликт авторов] Поглощение: '{old_path.name}' ──> '{new_filename}'")

                        try:
                            # Обходим содержимое грязного каталога автора
                            for item in list(old_path.iterdir()):
                                target_item = new_path / item.name

                                if item.is_dir():
                                    # Если папка серии уже есть в чистом авторе — сливаем файлы внутри неё
                                    if target_item.exists():
                                        for sub_item in list(item.iterdir()):
                                            dest_file = target_item / sub_item.name
                                            # Если файл книги с таким именем уже есть — перезапишем (дуэль размеров будет на Шаге 4)
                                            shutil.move(str(sub_item), str(target_item))
                                        item.rmdir()
                                    else:
                                        # Если серии в чистом авторе ещё нет — переносим её целиком
                                        shutil.move(str(item), str(new_path))
                                else:
                                    # Переносим одиночную книгу из корня грязного автора
                                    shutil.move(str(item), str(new_path))

                            # Физически стираем опустевшую грязную папку автора
                            old_path.rmdir()
                            logging.info(f"  [Успех] Грязный каталог автора '{old_path.name}' полностью удален.")
                        except Exception as e:
                            logging.error(f"  Ошибка физического слияния папок авторов {old_path.name}: {e}")

                    # СЦЕНАРИЙ Б: Путь свободен — стандартное быстрое переименование на уровне ОС
                    else:
                        try:
                            old_path.rename(new_path)
                            author.folder_path = new_path  # Синхронизируем путь в памяти объектов
                            logging.info(f"  Папка автора нормализована: '{old_path.name}' ──> '{new_filename}'")
                        except Exception as e:
                            logging.error(f"  Не удалось переименовать папку автора '{old_path.name}': {e}")
