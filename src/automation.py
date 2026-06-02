#-------------------------------------------------------------
# module: src/automation.py
#-------------------------------------------------------------

import logging
from typing import Dict, List
from library_class import Library
from automation_norm_library import automation_norm_library
from automation_norm_series import automation_norm_series
from automation_norm_book_name import automation_norm_book_name
from automation_join_series import automation_join_series
from automation_dedup_authors import automation_dedup_authors


def normalize_and_process_library(library: Library):
    """
    Последовательно выполняет все действия по нормализации структуры.
    Исправлен эффект 'второго запуска' за счет повторной зачистки после слияния авторов.
    """
    logging.info(f"=== Старт комплексной нормализации для: {library.base_path} ===")

    library.scan()
    initial_books_count = len(library.get_all_books())
    book_cfg = library.config.get("book", {})
    author_cfg = library.config.get("author", {})
    replaces = dict(book_cfg.get("title_substr", []))
    # Инициализируем глобальный счетчик статистики
    stats = {
        "deleted_books": 0,
        "merged_series": 0,
        "merged_authors": 0
    }
    # Первичная очистка структуры
    automation_norm_library(library)       # Шаг 1: Авторы
    automation_norm_series(library, replaces) # Шаг 2: Серии
    automation_norm_book_name(library, book_cfg, stats) # Шаг 3: Книги
    automation_join_series(library, stats)        # Шаг 4: Слияние серий

    # Глобальное слияние авторов (перемещает папки серий на новые места)
    automation_dedup_authors(library, author_cfg, stats) # Шаг 5: Слияние авторов

    # 🔥 ФИНАЛЬНЫЙ АККОРД: Схлопываем серии, которые съехались вместе после Шага 5
    if author_cfg.get("authors_deduplicate", True):
        logging.info("Повторная зачистка: Схлопывание серий, объединившихся после слияния авторов...")
        automation_norm_book_name(library, book_cfg, stats) # На всякий случай обновляем пути книг
        automation_join_series(library, stats)              # Склеиваем "Сагу Содружества" и "Сагу о Содружестве"

    final_books_count = len(library.get_all_books())
    logging.info("=========================================================")
    logging.info("🎉 ИТОГОВАЯ СТАТИСТИКА КОМПЛЕКСНОЙ НОРМАЛИЗАЦИИ:")
    logging.info(f" 📚 Всего книг до обработки:      {initial_books_count}")
    logging.info(f" 📚 Всего книг после обработки:   {final_books_count}")
    logging.info(f" ❌ Удалено дубликатов книг:      {stats['deleted_books']}")
    logging.info(f" 📂 Объединено дубликатов серий:  {stats['merged_series']}")
    logging.info(f" 👤 Объединено дубликатов авторов: {stats['merged_authors']}")
    logging.info("=========================================================")