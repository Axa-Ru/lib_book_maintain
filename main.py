import sys
import os
import logging

# Импорт разработанных нами компонентов системы
# Реальные пути импорта зависят от структуры вашего каталога src
from config_parser import load_and_parse_config
from library_class import Library
from automation import normalize_and_process_library
from merger import merge_libraries

import logging

def setup_logging(config: dict):
    """Настройка глобального вывода логов в файл на основе конфигурации TOML."""
    common_cfg = config.get("common", {})
    if common_cfg.get("enable_logs", True):
        log_level = logging.INFO
    else:
        log_level = logging.ERROR

    # путь к файлу лога
    log_file_path = common_cfg.get("log_file", "library.log")

    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - [%(levelname)s] - %(message)s',
        handlers=[
            # mode='w' очищает файл при каждом запуске.
            logging.FileHandler(log_file_path, mode='w', encoding='utf-8')
        ],
        force=True  # 🔥 ПРИНУДИТЕЛЬНО перезаписывает настройки логгера и активирует FileHandler
    )



def main():
    config_path = "profile/traum.toml"  # Конфиг лежит в папке profile, как указано в ТЗ

    # 1. Загрузка и валидация конфигурации
    try:
        config_data = load_and_parse_config(config_path)
    except FileNotFoundError as e:
        print(f"❌ Ошибка конфигурации: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Критическая ошибка при чтении конфига: {e}")
        sys.exit(1)

    # 2. Инициализация системы логирования
    setup_logging(config_data)
    logging.info("🚀 Запуск конвейера управления и синхронизации библиотек...")

    # =========================================================================
    # ЭТАП 1: Инициализация и нормализация ОСНОВНОЙ библиотеки
    # =========================================================================
    logging.info("--- ЭТАП 1: Обработка основной библиотеки ---")

    # Создаем конфиг специально для основной библиотеки (флаг use_test = false)
    main_config = config_data.copy()
    main_library = Library(config=main_config)

    # Запускаем первичную нормализацию (чистка серий, книг, внутренних дублей авторов)
    normalize_and_process_library(main_library)


    # =========================================================================
    # ЭТАП 2: Нормализация библиотеки-КАНДИДАТА и её сЛИЯНИЕ с основной (при флаге join_lib)
    # =========================================================================
    if config_data.get("libs", {}).get("join_lib", False):
        logging.info("--- ЭТАП 2: Обнаружен флаг join_lib. Запуск процесса слияния ---")

        # Создаем конфиг для библиотеки-кандидата (переключаем флаг на тестовый/кандидатский путь)
        candidate_config = config_data.copy()
        candidate_config["paths"]["use_test"] = True

        candidate_library = Library(config=candidate_config)

        # 2.1 Первичная нормализация структуры кандидата (чтобы структуры совпали с эталоном)
        logging.info("Выполняется предварительная нормализация кандидата...")
        normalize_and_process_library(candidate_library)

        # 2.2 Физический перенос книг и авторов из кандидата в основную
        logging.info("Запуск физического слияния файлов...")
        merge_libraries(main_library, candidate_library)


        # =========================================================================
        # ЭТАП 3: Повторная нормализация основной библиотеки (Финальная зачистка)
        # =========================================================================
        logging.info("--- ЭТАП 3: Финальная нормализация объединенной базы ---")
        logging.info("Перепроверка авторов и устранение наложений после слияния...")
        normalize_and_process_library(main_library)

    else:
        logging.info("--- ЭТАП 2: Слияние пропущено (флаг join_lib = false) ---")

    # 4. Вывод итоговой статистики в консоль
    final_books = main_library.get_all_books()
    logging.info("=========================================================================")
    logging.info(f"🎉 Процесс успешно завершен!")
    logging.info(f"📚 Итоговое количество книг в основной библиотеке: {len(final_books)}")
    logging.info("=========================================================================")

if __name__ == "__main__":
    main()
