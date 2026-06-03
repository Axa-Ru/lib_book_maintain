#-------------------------------------------------------------
# module: src/automation_norm_series.py
#-------------------------------------------------------------
from library_class import Library
from utils import replace_latin_with_cyrillic
import logging

def automation_norm_series(library: 'Library', replaces: dict) -> int:
    # === ШАГ 2: Нормализация названий серий и их папок ===
    logging.info("Шаг 2: Нормализация названий серий...")
    for lang, letters in library.catalog.items():
        for letter, authors in letters.items():
            for author in authors:
                for series in author.series_list:
                    if not series.is_virtual:
                        old_name = series.name
                        new_name = series.sanitize_name(replaces)
                        # Защита от скрытой латиницы в сериях
                        if lang.lower() == "ru" and new_name:
                            new_name = replace_latin_with_cyrillic(new_name)

                        if old_name != new_name and new_name:
                            old_path = author.folder_path / old_name
                            new_path = author.folder_path / new_name
                            if old_path.exists() and not new_path.exists():
                                try:
                                    old_path.rename(new_path)
                                    logging.info(f"  Серия: '{old_name}' -> '{new_name}'")
                                except Exception as e:
                                    logging.error(f"  Не удалось переименовать папку серии {old_path}: {e}")

    library.scan()