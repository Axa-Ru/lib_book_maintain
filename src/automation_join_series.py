#-------------------------------------------------------------
# module: src/automation_join_series.py
#-------------------------------------------------------------

from library_class import Library
import logging

def automation_join_series(library: 'Library', stats: dict):
    logging.info("Шаг 3: Поиск и объединение похожих серий внутри авторов...")
    for lang, letters in library.catalog.items():
        for letter, authors in letters.items():
            for author in authors:

                # Создаем копию списка серий для безопасного удаления в цикле
                real_series_list = [s for s in author.series_list if not s.is_virtual and s.name.strip()]
                processed_series_paths = set()

                for i in range(len(real_series_list)):
                    series_a = real_series_list[i]
                    path_a = author.folder_path / series_a.name
                    if path_a in processed_series_paths:
                        continue

                    for j in range(i + 1, len(real_series_list)):
                        series_b = real_series_list[j]
                        path_b = author.folder_path / series_b.name
                        if path_b in processed_series_paths:
                            continue

                        # ЧИСТЫЙ ООП-ВЫЗОВ: Серия сама сопоставляет себя с другой серией
                        if series_a.is_same_as(series_b, library.config):
                            #logging.info(
                            #    f"  [Серии-дубли] Совпадение серий у автора {author.name}: '{series_a.name}' <──> '{series_b.name}'")

                            # Приоритет отдаем более полному/длинному названию папки
                            if len(series_a.name) >= len(series_b.name):
                                series_primary = series_a
                                series_secondary = series_b
                            else:
                                series_primary = series_b
                                series_secondary = series_a

                            # Безопасное ООП-слияние файлов и зачистка папки
                            success = series_secondary.join_with(series_primary, author.folder_path)

                            if success:
                                stats["merged_series"] += 1
                                logging.info(
                                    f" Объединены серии: {series_secondary.name} ──> {series_primary.name}")
                                processed_series_paths.add(author.folder_path / series_secondary.name)

                                if series_primary == series_b:
                                    break

    library.scan()
