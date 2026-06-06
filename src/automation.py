# -------------------------------------------------------------
# module: src/automation.py
# -------------------------------------------------------------

import logging
from src.library_class import Library
from src.automation_norm_library import automation_norm_library
from src.automation_norm_series import automation_norm_series
from src.automation_join_series import automation_join_series
from src.automation_norm_book_name import automation_norm_book_name
from src.automation_dedup_books import automation_dedup_books
from src.automation_dedup_authors import automation_dedup_authors


def normalize_and_process_library(library: 'Library'):
    """
    [Версия 0.9.4] Главный оркестратор конвейера автоматизации.
    Линейно координирует шаги обработки. Все костыли прогрева кэша удалены.
    Синхронизация памяти и диска полностью делегирована штатному library.scan().
    """
    logging.info(f"=== Старт комплексной нормализации для: {library.base_path} ===")

    # 0. Первичная валидация архитектуры и первый сбор данных в память
    library.validate_structure()
    library.scan()

    book_cfg = library.config.get("book", {})
    author_cfg = library.config.get("author", {})
    replaces = dict(book_cfg.get("title_substr", []))

    stats = {
        "deleted_books": 0,
        "merged_series": 0,
        "merged_authors": 0
    }

    # =====================================================================
    # ЭТАП 1: Выравнивание структуры контейнеров (Папок)
    # =====================================================================

    # Шаг 1: Нормализация имен авторов
    automation_norm_library(library)
    library.scan()

    # Шаг 2: Нормализация названий серий
    automation_norm_series(library, replaces)
    library.scan()

    # Шаг 3: Слияние похожих папок серий внутри авторов (rapidfuzz)
    automation_join_series(library, stats)
    library.scan()

    # =====================================================================
    # ЭТАП 2: Выравнивание и дедупликация контента (Файлов книг)
    # =====================================================================

    # Шаг 4: Нормализация имен файлов книг (с жестким усечением длин)
    automation_norm_book_name(library, book_cfg, stats)
    library.scan()

    # Шаг 4.5: Кросс-серийное схлопывание дубликатов (Корень автора <──> Подпапки серий)
    automation_dedup_books(library, stats)
    library.scan()

    # =====================================================================
    # ЭТАП 3: Глобальное индексное слияние авторов
    # =====================================================================

    # Шаг 5: Поиск и объединение дубликатов авторов (Каскадная дедупликация по Фамилиям)
    if author_cfg.get("authors_deduplicate", True):
        automation_dedup_authors(library, author_cfg, stats)
        library.scan()

        # Финальный каскадный аккорд: схлопываем серии, съехавшиеся вместе после Шага 5
        logging.info("Повторная зачистка: Схлопывание серий, объединившихся после слияния авторов...")
        automation_join_series(library, stats)
        library.scan()

    logging.info("=========================================================")
    logging.info("🎉 ИТОГОВАЯ СТАТИСТИКА КОМПЛЕКСНОЙ НОРМАЛИЗАЦИИ:")
    logging.info(f"  ❌ Удалено дубликатов книг:      {stats['deleted_books']}")
    logging.info(f"  📂 Объединено дубликатов серий:  {stats['merged_series']}")
    logging.info(f"  👤 Объединено дубликатов авторов: {stats['merged_authors']}")
    logging.info("=========================================================")
