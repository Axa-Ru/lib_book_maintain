# -------------------------------------------------------------
# module: src/automation_dedup_authors.py
# -------------------------------------------------------------

import re
import logging
from typing import Dict, List
from library_class import Library
from author_class import Author


def automation_dedup_authors(library: 'Library', author_cfg: dict, stats: dict):
    if author_cfg.get("authors_deduplicate", True):
        logging.info("Шаг 5: Поиск и объединение дубликатов авторов (Индексная дедупликация по Фамилиям)...")

        for lang, letters in library.catalog.items():
            for letter, authors_list in letters.items():

                # Построение высокопроизводительного индекса фамилий по полю TARGET-состояния (new_name)
                surname_index: Dict[str, List[Author]] = {}

                for author in authors_list:
                    # Извлекаем токены фамилии строго из вычисленного идеального имени
                    tokens = re.split(r'[.\s]+', author.new_name.strip())
                    clean_tokens = [t.lower().replace('ё', 'е') for t in tokens if t]

                    if clean_tokens:
                        surname = clean_tokens[0]
                        if surname not in surname_index:
                            surname_index[surname] = []
                        surname_index[surname].append(author)

                # Сравнение однофамильцев внутри изолированных корзин
                for surname, group in surname_index.items():
                    if len(group) < 2:
                        continue

                    processed_folders = set()
                    for i in range(len(group)):
                        author_a = group[i]
                        if author_a.folder_path in processed_folders:
                            continue

                        for j in range(i + 1, len(group)):
                            author_b = group[j]
                            if author_b.folder_path in processed_folders:
                                continue

                            if author_a == author_b or author_a.folder_path == author_b.folder_path:
                                continue  # 🔥 Жестко пропускаем, если это одна и та же папка на диске

                            # ООП-сравнение полей идеального состояния
                            if author_a.is_same_as(author_b, library.config):
                                logging.info(
                                    f"  [Автор-дубль] Совпадение: '{author_a.new_name}' <──> '{author_b.new_name}'")

                                comparison_result = author_a._compare_author_name(author_b)

                                if comparison_result == 1:
                                    author_primary = author_a
                                    author_secondary = author_b
                                else:
                                    author_primary = author_b
                                    author_secondary = author_a

                                success = author_secondary.join_with(author_primary)
                                if success:
                                    if stats: stats["merged_authors"] += 1
                                    logging.info(
                                        f"  Успешно объединены: {author_secondary.new_name} ──> {author_primary.new_name}")
                                    processed_folders.add(author_secondary.folder_path)

                                    if author_primary == author_b:
                                        break


