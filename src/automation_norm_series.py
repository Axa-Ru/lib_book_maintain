# -------------------------------------------------------------
# module: src/automation_norm_series.py
# -------------------------------------------------------------

import logging
import shutil
from pathlib import Path
from src.library_class import Library


def automation_norm_series(library: 'Library', replaces: dict):
    """
    [Версия 0.9.5] Шаг 2: Нормализация названий папок серий со слиянием.
    Исключает бесконечное зацикливание регистра букв на ext4.
    """
    logging.info("Шаг 2: Нормализация названий серий (с каскадным слиянием)...")
    lang_keys = list(library.catalog.keys())
    lang = lang_keys[0] if lang_keys else "ru"

    for lang_code, letters in library.catalog.items():
        for letter, authors in letters.items():
            for author in authors:
                for series in author.series_list:
                    if series.is_virtual:
                        continue

                    # Вычисляем идеальное целевое имя папки серии
                    series.compute_new_name(replaces, author.name, base_lang=lang_code)

                    old_path = author.folder_path / series.name
                    new_path = author.folder_path / series.new_name

                    # Если имя папки серии на диске отличается от вычисленного идеала
                    if old_path.exists() and series.name != series.new_name:

                        # СЦЕНАРИЙ А: Целевая папка серии уже физически стоит на диске
                        if new_path.exists():
                            logging.info(
                                f"  [Конфликт серий] Слияние папок: '{series.name}' ──> '{series.new_name}' у {author.name}")
                            try:
                                # Эвакуируем все файлы книг в правильную папку серии
                                for file_item in list(old_path.iterdir()):
                                    if file_item.is_file() and file_item.suffix.lower() == '.epub':
                                        shutil.move(str(file_item), str(new_path))

                                # Стираем пустую старую ветку серии
                                old_path.rmdir()
                            except Exception as e:
                                logging.error(f"  Ошибка слияния регистров папок серий для {series.name}: {e}")

                        # СЦЕНАРИЙ Б: Путь чист — стандартный rename
                        else:
                            try:
                                old_path.rename(new_path)
                                logging.info(f"  Серия нормализована: '{series.name}' ──> '{series.new_name}'")
                            except Exception as e:
                                logging.error(f"  Не удалось переименовать папку серии '{series.name}': {e}")
