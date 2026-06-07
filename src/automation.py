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
    [Версия 0.9.6] Главный оркестратор конвейера автоматизации.
    Линейно координирует шаги обработки, передавая плоский список авторов в модули.
    Синхронизация памяти и диска полностью делегирована методу library.scan().
    """
    logging.info(f"=== Старт комплексной нормализации для: {library.base_path} ===")

    # 0. Валидация структуры каталогов и первичный сбор данных в память
    library.validate_structure()
    library.scan()

    book_cfg = library.config.get("book", {})
    author_cfg = library.config.get("author", {})
    replaces = dict(book_cfg.get("title_substr", []))

    # Сводный глобальный счетчик за всю сессию автоматизации
    stats = {
        "deleted_books": 0,
        "merged_series": 0,
        "merged_authors": 0
    }

    turn_count = 1
    while True:
        logging.info(f"🔄 Запуск витка конвейера автоматизации №{turn_count}...")

        # Запоминаем показатели счетчиков строго НА СТАРТЕ текущего витка
        start_deleted = stats["deleted_books"]
        start_series = stats["merged_series"]
        start_authors = stats["merged_authors"]

        # =====================================================================
        # ЭТАП 1: Выравнивание структуры контейнеров (Папок авторов и серий)
        # =====================================================================

        # Шаг 1: Нормализация имен авторов на диске
        automation_norm_library(library)
        library.scan()  # Синхронизируем диск с памятью

        # Шаг 2: Нормализация названий папок серий
        automation_norm_series(library, replaces)
        library.scan()

        # 🔥 ФИКС ТИПА: Извлекаем плоский список авторов из трехмерного каталога
        flat_authors = []
        for lang, letters in library.catalog.items():
            for letter, authors_list in letters.items():
                flat_authors.extend(authors_list)

        # Шаг 3: Слияние похожих папок серий внутри авторов (rapidfuzz)
        automation_join_series(flat_authors, stats)
        library.scan()

        # =====================================================================
        # ЭТАП 2: Выравнивание и дедупликация контента (Файлов книг)
        # =====================================================================

        # Пересобираем плоский список авторов после ре-сканирования
        flat_authors = []
        for lang, letters in library.catalog.items():
            for letter, authors_list in letters.items():
                flat_authors.extend(authors_list)

        # Шаг 4: Нормализация имен файлов книг (с жестким усечением длин)
        automation_norm_book_name(flat_authors, book_cfg, stats)
        library.scan()

        # Пересобираем плоский список авторов после ре-сканирования
        flat_authors = []
        for lang, letters in library.catalog.items():
            for letter, authors_list in letters.items():
                flat_authors.extend(authors_list)

        # Шаг 4.5: Кросс-серийное схлопывание дубликатов (Корень автора <──> Подпапки серий)
        automation_dedup_books(flat_authors, stats)
        library.scan()

        # =====================================================================
        # ЭТАП 3: Глобальное индексное слияние авторов
        # =====================================================================

        # Шаг 5: Поиск и объединение дубликатов авторов (Каскадная дедупликация)
        if author_cfg.get("authors_deduplicate", True):
            automation_dedup_authors(library, author_cfg, stats)
            library.scan()

            # Финальный каскадный аккорд: собираем список заново и схлопываем серии,
            # съехавшиеся вместе после Шаг 5
            flat_authors = []
            for lang, letters in library.catalog.items():
                for letter, authors_list in letters.items():
                    flat_authors.extend(authors_list)

            logging.info(f"  [Виток {turn_count}] Повторная зачистка серий, объединившихся после авторов...")
            automation_join_series(flat_authors, stats)
            library.scan()

        # 🔥 ВЫЧИСЛЯЕМ КОЛИЧЕСТВО ИЗМЕНЕНИЙ СТРОГО ЗА ТЕКУЩИЙ ВИТОК
        current_turn_changes = (
                (stats["deleted_books"] - start_deleted) +
                (stats["merged_series"] - start_series) +
                (stats["merged_authors"] - start_authors)
        )

        logging.info(f"📊 Виток конвейера №{turn_count} завершен. Изменений за проход: {current_turn_changes}")

        # Критерий останова для достижения идемпотентности
        if current_turn_changes == 0:
            logging.info(f"✨ Конвейер пришел в состояние стабильности на витке {turn_count}. Безопасный выход.")
            break

        turn_count += 1

    # Вывод финального триумфального отчета
    logging.info("=========================================================")
    logging.info("🎉 ИТОГОВАЯ СУММАРНАЯ СТАТИСТИКА КОМПЛЕКСНОЙ НОРМАЛИЗАЦИИ:")
    logging.info(f"  ❌ Всего удалено дубликатов книг:      {stats['deleted_books']}")
    logging.info(f"  📂 Всего объединено дубликатов серий:  {stats['merged_series']}")
    logging.info(f"  👤 Всего объединено дубликатов авторов: {stats['merged_authors']}")
    logging.info("=========================================================")
