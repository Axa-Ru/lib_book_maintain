# -------------------------------------------------------------
# module: src/automation_join_series.py
# -------------------------------------------------------------

import logging
from library_class import Library


def automation_join_series(library: 'Library', stats: dict):
    """
    [Версия 0.9.3] Шаг 3: Поиск и объединение похожих серий внутри авторов.
    Сравнивает и склеивает дублирующиеся папки серий (например, "Сага Содружества" и "Сага о Содружестве"),
    физически перенося книги в одну общую папку.
    """
    logging.info("Шаг 3: Поиск и объединение похожих серий внутри авторов...")

    for lang, letters in library.catalog.items():
        for letter, authors in letters.items():
            for author in authors:

                # Собираем актуальный список реальных серий автора по их текущему физическому имени
                real_series_list = [s for s in author.series_list if not s.is_virtual and s.name.strip()]
                processed_series_names = set()

                for i in range(len(real_series_list)):
                    series_a = real_series_list[i]
                    if series_a.name in processed_series_names:
                        continue

                    for j in range(i + 1, len(real_series_list)):
                        series_b = real_series_list[j]
                        if series_b.name in processed_series_names:
                            continue

                        # ООП-ВЫЗОВ: Серия сопоставляет свои токены target-состояния (new_name)
                        if series_a.is_same_as(series_b, library.config):

                            # Приоритет отдаем более полному/длинному названию папки
                            if len(series_a.name) >= len(series_b.name):
                                series_primary = series_a
                                series_secondary = series_b
                            else:
                                series_primary = series_b
                                series_secondary = series_a

                            # Выполняем физический перенос уникальных книг на диске и удаление пустой папки
                            success = series_secondary.join_with(series_primary, author.folder_path)

                            if success:
                                if stats: stats["merged_series"] += 1
                                logging.info(
                                    f"  Объединены серии: '{series_secondary.name}' ──> '{series_primary.name}'")

                                # Помечаем поглощенную серию как удаленную, чтобы процессор больше её не трогал
                                processed_series_names.add(series_secondary.name)

                                # Если поглощающей серией оказалась серия B, прерываем внутренний цикл,
                                # так как текущая серия A только что была физически уничтожена
                                if series_primary == series_b:
                                    break

