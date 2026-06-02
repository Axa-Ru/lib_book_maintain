# -------------------------------------------------------------
# module: src/automation_dedup_authors.py
# -------------------------------------------------------------

import re
import logging
from typing import Dict, List
from library_class import Library
from author_class import Author


def automation_dedup_authors(library: 'Library', author_cfg: dict):
    if author_cfg.get("authors_deduplicate", True):
        logging.info("Шаг 5: Поиск и объединение дубликатов авторов (Индексная дедупликация по Фамилиям)...")

        for lang, letters in library.catalog.items():
            for letter, authors_list in letters.items():

                # 1. СТРОИМ ИНДЕКС ФАМИЛИЙ ДЛЯ ТЕКУЩЕЙ БУКВЫ
                # Структура: { "иванов": [Author_obj1, Author_obj2], "петров": [...] }
                surname_index: Dict[str, List[Author]] = {}

                for author in authors_list:
                    # Извлекаем токены ФИО так же, как в методе is_same_as
                    tokens = re.split(r'[.\s]+', author.name.strip())
                    clean_tokens = [t.lower().replace('ё', 'е') for t in tokens if t]

                    if clean_tokens:
                        surname = clean_tokens[0]  # Фамилия — всегда первый токен
                        if surname not in surname_index:
                            surname_index[surname] = []
                        surname_index[surname].append(author)

                # 2. СРАВНИВАЕМ АВТОРОВ СТРОГО ВНУТРИ ГРУПП ОДНОФАМИЛЬЦЕВ
                for surname, group in surname_index.items():
                    # Если фамилия уникальна и автор один — пропускаем, дубликатов нет
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

                            # ООП-ВЫЗОВ: Сравнение идет только между потенциальными однофамильцами
                            if author_a.is_same_as(author_b, library.config):
                                logging.info(
                                    f"  [Автор-дубль] Найдено совпадение автора: '{author_a.name}' <──> '{author_b.name}'")

                                # Вычисляем приоритет ФИО (с учетом буквы 'ё')
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
                                    logging.info(
                                        f"  Успешно объединены: {author_secondary.name} ──> {author_primary.name}")
                                    processed_folders.add(author_secondary.folder_path)

                                    if author_primary == author_b:
                                        break

        # Один финальный скан на весь модуль, чтобы обновить состояние в памяти Library
        library.scan()
