#-------------------------------------------------------------
# module: src/automation_dedup_authors.py
#-------------------------------------------------------------

from typing import Dict, List
from library_class import Library
from author_class import Author
import logging

def automation_dedup_authors(library: 'Library', author_cfg: dict):
    if author_cfg.get("authors_deduplicate", True):
        logging.info("Шаг 5: Поиск и объединение дубликатов авторов...")
        for lang, letters in library.catalog.items():
            all_authors_in_lang: List[Author] = []
            for letter, authors in letters.items():
                all_authors_in_lang.extend(authors)

            processed_folders = set()
            for i in range(len(all_authors_in_lang)):
                author_a = all_authors_in_lang[i]
                if author_a.folder_path in processed_folders:
                    continue

                for j in range(i + 1, len(all_authors_in_lang)):
                    author_b = all_authors_in_lang[j]
                    if author_b.folder_path in processed_folders:
                        continue

                    # ЧИСТЫЙ ООП-ВЫЗОВ: Автор сам каскадно сопоставляет себя со вторым автором
                    if author_a.is_same_as(author_b, library.config):
                        #logging.info(
                        #    f"  [Автор-дубль] Найдено совпадение автора: '{author_a.name}' <──> '{author_b.name}'")

                        # Вычисляем приоритет ФИО (с учетом правильной буквы 'ё')
                        comparison_result = author_a._compare_author_name(author_b)

                        if comparison_result == 1:
                            author_primary = author_a
                            author_secondary = author_b
                        else:
                            author_primary = author_b
                            author_secondary = author_a

                        # Физический перенос уникальных книг и зачистка папки
                        success = author_secondary.join_with(author_primary)
                        if success:
                            logging.info(f" объединены: {author_secondary.name} ──> {author_primary.name}")
                            processed_folders.add(author_secondary.folder_path)

                            if author_primary == author_b:
                                break

        library.scan()

