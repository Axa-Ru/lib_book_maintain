# -------------------------------------------------------------
# module: src/automation_norm_series.py
# -------------------------------------------------------------

import logging
from library_class import Library


def automation_norm_series(library: 'Library', replaces: dict) -> None:
    """
    [Версия 0.9.3] Шаг 2: Нормализация названий серий и их папок.
    Каждая серия сама рассчитывает своё целевое идеальное имя (new_name),
    после чего происходит безопасное физическое переименование папки на диске.
    """
    logging.info("Шаг 2: Нормализация названий серий...")

    for lang, letters in library.catalog.items():
        # lang гарантированно содержит строковый код зоны ("ru" или "en")

        for letter, authors in letters.items():
            for author in authors:
                for series in author.series_list:
                    if not series.is_virtual:

                        # 1. Объект серии сам рассчитывает своё идеальное состояние (new_name).
                        # Передаем строковую переменную lang напрямую в base_lang.
                        series.compute_new_name(replaces, author.name, base_lang=lang)

                        # 2. Сравниваем текущее физическое имя на диске с вычисленным идеалом
                        if series.new_name and series.name != series.new_name:
                            old_path = author.folder_path / series.name
                            new_path = author.folder_path / series.new_name

                            # Проверяем физическое наличие исходной папки и отсутствие целевой
                            if old_path.exists() and not new_path.exists():
                                try:
                                    old_path.rename(new_path)
                                    logging.info(f"  Серия: '{series.name}' -> '{series.new_name}'")

                                    # Переименование прошло успешно — синхронизируем физическое имя в памяти
                                    series.name = series.new_name
                                except Exception as e:
                                    logging.error(f"  Не удалось переименовать папку серии {old_path}: {e}")
                            elif new_path.exists():
                                logging.warning(
                                    f"  Целевая папка серии '{series.new_name}' уже существует на диске. "
                                    f"  Слияние содержимого произойдет на Шаге 4 (automation_join_series)."
                                )

