# -------------------------------------------------------------
# module: src/automation_norm_library.py
# -------------------------------------------------------------

import logging
from library_class import Library

# -------------------------------------------------------------
# module: src/automation_norm_library.py
# -------------------------------------------------------------

import logging
from library_class import Library


def automation_norm_library(library: 'Library') -> None:
    logging.info("Шаг 1: Нормализация имен авторов...")
    for lang, letters in library.catalog.items():
        # lang содержит "ru" или "en" — передаем эту строку как base_lang

        for letter, authors in letters.items():
            for author in authors:
                # 1. 🔥 ИСПРАВЛЕНО: Передаем строковый идентификатор языка ("ru"/"en")
                author.compute_new_name(base_lang=lang)

                # 2. Сравниваем физическое имя на диске с вычисленным идеалом
                if author.new_name and author.name != author.new_name:
                    old_path = author.folder_path
                    new_path = author.folder_path.parent / author.new_name

                    if old_path.exists() and not new_path.exists():
                        try:
                            old_path.rename(new_path)
                            author.folder_path = new_path  # Синхронизируем путь в памяти
                            author.name = author.new_name  # Синхронизируем физическое имя
                            logging.info(f"  Автор: '{old_path.name}' -> '{author.new_name}'")
                        except Exception as e:
                            logging.error(f"  Не удалось переименовать папку автора {old_path}: {e}")
                    elif new_path.exists():
                        logging.warning(f"  Папка '{author.new_name}' уже существует. Слияние произойдет на Шаге 5.")


