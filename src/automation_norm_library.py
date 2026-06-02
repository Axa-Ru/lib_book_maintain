#-------------------------------------------------------------
# module: src/automation_norm_library.py
#-------------------------------------------------------------

from library_class import Library
import logging

def automation_norm_library(library: 'Library') -> None:
    logging.info("Шаг 1: Нормализация имен авторов...")
    for lang, letters in library.catalog.items():
        for letter, authors in letters.items():
            for author in authors:
                old_folder_name = author.name

                # Метод очищает ФИО и перезаписывает self.name внутри объекта
                author._normalize_name()
                new_folder_name = author.name

                # Если имя изменилось, синхронизируем физическую папку на диске
                if old_folder_name != new_folder_name:
                    old_path = author.folder_path
                    new_path = author.folder_path.parent / new_folder_name

                    if old_path.exists() and not new_path.exists():
                        try:
                            old_path.rename(new_path)
                            author.folder_path = new_path  # Обновляем путь в объекте
                            logging.info(f"  Автора: '{old_folder_name}' -> '{new_folder_name}'")
                        except Exception as e:
                            logging.error(f"  Не удалось переименовать папку автора {old_path}: {e}")
                    elif new_path.exists():
                        logging.warning(f"  Папка '{new_folder_name}' уже существует. Слияние произойдет на Шаге 5.")

    library.scan()
