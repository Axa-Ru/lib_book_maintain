# -------------------------------------------------------------
# module: src/automation_join_series.py
# -------------------------------------------------------------

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

def automation_join_series(authors: List[Any], stats: Optional[Dict[str, Any]] = None) -> int:
    """
    [Версия 0.9.6] Поиск и объединение похожих серий внутри каждого автора.
    Устраняет дубликаты, возникшие из-за разницы в регистре символов (Case-Insensitive).
    Синхронизирован со списком структуры серий author.series_list.
    """
    if stats is None:
        stats = {"merged_series": 0}

    local_merged_count = 0
    # Кэш имен в нижнем регистре для предотвращения межвиткового зацикливания
    processed_series_names = set()

    for author in authors:
        # 🔥 ФИКС 1: Проверяем реальное свойство списочной структуры автора
        if not hasattr(author, 'series_list') or not author.series_list:
            continue

        # 🔥 ФИКС 2: Итерируем по изолированной копии списка серий автора
        current_series_list = list(author.series_list)

        for i, series_secondary in enumerate(current_series_list):
            # Виртуальную серию для одиночных книг из корня пропускаем — она не сливается как папка
            if series_secondary.is_virtual:
                continue

            # Если серия уже была поглощена ранее, пропускаем её
            sec_name_lower = series_secondary.name.lower()
            if sec_name_lower in processed_series_names:
                continue

            # Ищем, с какой серией из оставшихся можно слить текущую
            for series_primary in current_series_list[i + 1:]:
                if series_primary.is_virtual:
                    continue

                prim_name_lower = series_primary.name.lower()

                # Если серии уже обработаны или это одна и та же серия в памяти — пропускаем
                if prim_name_lower in processed_series_names or series_secondary == series_primary:
                    continue

                # Условие дублирования: совпадение имен без учета регистра символов
                if sec_name_lower == prim_name_lower:

                    # Получаем путь к папке автора (поддерживаем как строки, так и Path)
                    author_folder = Path(author.folder_path) if hasattr(author, 'folder_path') else Path(author.path)

                    # Вызываем физическое слияние папок на диске [Метод Версии 0.9.5]
                    success = series_secondary.join_with(series_primary, author_folder)

                    if success:
                        local_merged_count += 1
                        stats["merged_series"] += 1

                        # Извлекаем имена авторов для логов с защитой от отсутствующих атрибутов
                        author_old = getattr(author, 'name', 'Unknown')
                        author_new = getattr(author, 'new_name', author_old)

                        logging.info(f"  Автор: Старое имя : {author_old}")
                        logging.info(f"  Автор: Новое имя  : {author_new}")
                        logging.info(f"  Объединены серии  : '{series_secondary.name}' ──> '{series_primary.name}'")

                        # ФИКС ЗАЦИКЛИВАНИЯ 1: Маркируем обе серии в нижнем регистре
                        processed_series_names.add(sec_name_lower)
                        processed_series_names.add(prim_name_lower)

                        # 🔥 ФИКС 3: Удаляем поглощенный объект из списка ОЗУ автора.
                        if series_secondary in author.series_list:
                            author.series_list.remove(series_secondary)

                        # Так как текущая secondary-серия уничтожена, выходим к следующей
                        break

    return local_merged_count
