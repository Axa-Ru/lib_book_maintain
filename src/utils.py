# -----------------------------------------------------------------------
# module: src/utils.py
# Утилиты
# -----------------------------------------------------------------------
import logging
import re

# Заранее компилируем регулярные выражения для максимальной скорости на 500 000 книг
_RE_MULTIPLE_SPACES = re.compile(r'\s+')
_RE_TRAILING_DOTS_SPACES = re.compile(r'[\s\.]+$')
_RE_PUNCTUATION_TOKENS = re.compile(r'(\s+|[()\[\]\{\}\.\,\-\+])')
_RE_IS_PUNCTUATION = re.compile(r'^[\s()\[\]\{\}\.\,\-\+]+$')

# =====================================================================
# ЕДИНАЯ ТОЧКА НАСТРОЙКИ СИМВОЛОВ-ДВОЙНИКОВ (КИРИЛЛИЦА <-> ЛАТИНИЦА)
# =====================================================================
_RAW_LAT_TO_CYR = {
    'A': 'А', 'B': 'В', 'E': 'Е', 'H': 'Н', 'K': 'К', 'M': 'М',
    'O': 'О', 'P': 'Р', 'C': 'С', 'T': 'Т', 'X': 'Х',
    'a': 'а', 'e': 'е', 'o': 'о', 'p': 'р', 'c': 'с', 'x': 'х'
}

# Строим официальные таблицы трансляции Python
_LAT_TO_CYR = str.maketrans(_RAW_LAT_TO_CYR)
_CYR_TO_LAT = str.maketrans({cyr: lat for lat, cyr in _RAW_LAT_TO_CYR.items()})

# Динамическая сборка наборов символов напрямую из карты замен
_LAT_TWINS_SET = set(_RAW_LAT_TO_CYR.keys())
_CYR_TWINS_SET = set(_RAW_LAT_TO_CYR.values())


# =====================================================================

def sanitize_text_base(text: str, base_lang: str = "ru") -> str:
    """
    [Версия 0.9.3] Общесистемная базовая очистка строки:
    1. Убирает множественные пробелы внутри строки.
    2. Удаляет пробелы и точки на концах строки.
    3. Выполняет умную токенизированную конвертацию раскладок (Мажоритарное голосование).
    """
    if not text:
        return ""

    lang = base_lang.strip().lower()
    if lang not in ("ru", "en"):
        raise ValueError(
            f"Критическая ошибка: Неподдерживаемая языковая зона base_lang='{base_lang}'. "
            f"Допустимые значения: 'ru' или 'en'."
        )

    # 1. Схлопываем множественные пробелы
    text = _RE_MULTIPLE_SPACES.sub(' ', text)

    # 2. Срезаем пробелы и точки на концах
    text = _RE_TRAILING_DOTS_SPACES.sub('', text)
    text = text.strip(' .')

    # 3. УМНАЯ КОНВЕРТАЦИЯ РАСКЛАДОК НА ОСНОВЕ ТОКЕНОВ (Защита мультиязычных строк)
    # Разбиваем строку на слова, сохраняя пробелы и любые скобки
    tokens = _RE_PUNCTUATION_TOKENS.split(text)

    processed_tokens = []
    for token in tokens:
        # Если токен пустой или состоит только из знаков препинания/пробелов — оставляем как есть
        if not token or _RE_IS_PUNCTUATION.match(token):
            processed_tokens.append(token)
            continue

        # Считаем буквы-двойники, используя наши централизованные наборы
        cyr_count = sum(1 for char in token if char in _CYR_TWINS_SET)
        lat_count = sum(1 for char in token if char in _LAT_TWINS_SET)

        # Проверяем наличие уникальных букв (железных признаков алфавита) за пределами двойников
        # Кириллический диапазон Unicode: от U+0400 до U+04FF (буквы 'б', 'ж', 'и' и т.д.)
        has_pure_cyr = any(u'\u0400' <= char <= u'\u04FF' for char in token if char not in _CYR_TWINS_SET)
        # Стандартная латиница ASCII без учета знаков и цифр (буквы 'q', 'w', 'z' и т.д.)
        has_pure_lat = any(char.isalpha() and ord(char) < 128 for char in token if char not in _LAT_TWINS_SET)

        # Добавляем весовые коэффициенты на основе уникальных букв алфавита
        if has_pure_cyr:
            cyr_count += 10
        if has_pure_lat:
            lat_count += 10

        # Мажоритарный выбор раскладки для конкретного слова на основе целевой зоны программы
        if lang == "ru":
            if cyr_count > lat_count:
                # В русском слове затесалась латиница — лечим её
                processed_tokens.append(token.translate(_LAT_TO_CYR))
            else:
                # Если это чисто английское слово в русской строке — защищаем и оставляем латиницей
                processed_tokens.append(token)
        elif lang == "en":
            if lat_count > cyr_count:
                # В английском слове затесалась кириллица — лечим её
                processed_tokens.append(token.translate(_CYR_TO_LAT))
            else:
                processed_tokens.append(token)

    return "".join(processed_tokens)


def capitalize_first_letters(text: str) -> str:
    """
    Делает заглавными первые буквы предложений, если текст вне скобок
    набран строчными буквами. Содержимое любых круглых () и квадратных []
    скобок всегда остается без изменений.
    """
    # Регулярное выражение находит любые блоки в круглых () или квадратных [] скобках
    brackets_pattern = re.compile(r'(\([^)]*\)|\[[^\]]*\])')

    # 1. Разбиваем строку на части: текст вне скобок и текст внутри скобок
    tokens = brackets_pattern.split(text)

    # 2. Проверяем, набран ли весь текст ВНЕ скобок строчными буквами.
    # Если за пределами скобок уже есть заглавные буквы, возвращаем строку без изменений.
    text_outside_brackets = "".join([t for t in tokens if not brackets_pattern.match(t)])
    if text_outside_brackets and not text_outside_brackets.islower():
        return text

    # Переменная-флаг, указывающая, что следующая встреченная буква должна стать заглавной.
    # В самом начале строки первая буква предложения всегда должна быть заглавной.
    next_is_capital = True

    # 3. Обрабатываем каждый токен последовательно
    for i, token in enumerate(tokens):
        # Если это блок в скобках, оставляем его полностью без изменений
        if brackets_pattern.match(token):
            continue

        # Если это текст вне скобок, обрабатываем его посимвольно
        chars = list(token)
        for j, char in enumerate(chars):
            if char.isalpha():
                if next_is_capital:
                    chars[j] = char.upper()
                    next_is_capital = False  # Буквица установлена, ждем новую точку
            elif char == '.':
                # Если встретили точку, значит следующее предложение потребует заглавную букву
                next_is_capital = True

        tokens[i] = "".join(chars)

    # 4. Собираем строку обратно из обработанных частей
    return "".join(tokens)


def replace_cyrillic_with_latin(text: str) -> str:
    return text.translate(_CYR_TO_LAT)


def replace_latin_with_cyrillic(text: str) -> str:
    return text.translate(_LAT_TO_CYR)


def apply_title_replacements(text: str, replacements: list) -> str:
    """
    Применяет список замен подстрок к переданному тексту на основе
    конфигурации title_substr. Очищает возникающие дубликаты пробелов.
    """
    if not text:
        return ""

    for old_value, new_value in replacements:
        # Используем обычный replace, так как строки замен фиксированные
        text = text.replace(old_value, new_value)

    # Убираем дублирующиеся пробелы, которые могли возникнуть после удаления подстрок
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def debug_string_character_codes(strings_list: list):
    """
    Принимает список строк и выводит в лог каждый символ
    вместе с его числовым кодом Unicode для поиска скрытых различий.
    """
    logging.info("=== посимвольный анализ списка строк ===")

    for word_index, string_value in enumerate(strings_list):
        logging.info(f"\nСтрока [{word_index}]: '{string_value}' (Длина: {len(string_value)} символов)")

        # Разбираем строку посимвольно
        char_details = []
        for char in string_value:
            char_code = ord(char)
            # Форматируем вывод: символ и его код (например, 'г': 1075)
            char_details.append(f"'{char}': {char_code}")

        # Собираем всё в одну строчку для удобства чтения лога
        logging.info("👉 Коды символов: " + " | ".join(char_details))


def fix_uppercase_text(text: str) -> str:
    """
    [Версия 0.9.3] Исправляет текст, написанный КАПСОМ,
    и гарантирует, что первая буква строки ВСЕГДА будет заглавной.
    """
    if not text:
        return ""

    # 1. Если вся строка написана капсом (например, "МИР ФАНТАСТИКИ") — нормализуем её
    if text.isupper():
        text = text.lower()

    # 2. 🔥 ЖЕЛЕЗНО: Делаем первую букву заглавной, сохраняя регистр остальных слов
    return text[0].upper() + text[1:] if len(text) > 1 else text.upper()



def strip_spaces_inside_brackets(text: str) -> str:
    """
    Убирает пробелы сразу после открывающих и перед закрывающими скобками.
    Пример: "( Межавторский цикл )" -> "(Межавторский цикл)"
    """
    if not text:
        return ""
    # Убираем пробелы после открывающих скобок
    text = re.sub(r'\(\s+', '(', text)
    text = re.sub(r'\[\s+', '[', text)

    # Убираем пробелы перед закрывающими скобками
    text = re.sub(r'\s+\)', ')', text)
    text = re.sub(r'\s+\]', ']', text)

    # Схлопываем случайные двойные пробелы, если они образовались
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def remove_author_name_from_text(text: str, author_name: str, min_limit: int = 8) -> str:
    """
    Вырезает имя автора из названия, предотвращая комбинаторные взрывы и сброс метаданных.
    """
    if not text or not author_name:
        return text

    author_tokens = [t.lower() for t in re.split(r'[.\s]+', author_name.strip()) if t and len(t) > 1]
    if not author_tokens:
        return text

    if " - " in text:
        parts = text.split(" - ", 1)
        author_part = parts[0]
        title_part = parts[1]

        temp_title = title_part
        has_changes = False

        for token in author_tokens:
            safe_token = re.escape(token)
            patterns = [
                rf'\[\s*{safe_token}\s*\]',
                rf'\(\s*{safe_token}\s*\)',
                rf'[\.\-\s\u00a0]+\b{safe_token}\b',
                rf'\b{safe_token}\b[\.\-\s\u00a0]+',
                rf'\b{safe_token}\b'
            ]
            for pattern in patterns:
                if re.search(pattern, temp_title, flags=re.IGNORECASE):
                    temp_title = re.sub(pattern, ' ', temp_title, flags=re.IGNORECASE)
                    has_changes = True

        if not has_changes:
            return text

        # Зачищаем артефакты после удаления
        temp_title = re.sub(r'\s*-\s*-*\s*', '-', temp_title)
        temp_title = re.sub(r'\s*[\.\,]\s*', ' ', temp_title)
        # 🔥 ИСПРАВЛЕНО: Корректное регулярное выражение без экранирования кавычки
        temp_title = re.sub(r'\s+', ' ', temp_title).strip(" .-")

        # ПРОВЕРКА ЛИМИТА: применяется ТОЛЬКО если текст реально изменился
        if not temp_title or (len(title_part) - len(temp_title) < min_limit):
            return text

        if temp_title:
            temp_title = temp_title[0].upper() + temp_title[1:]
        return f"{author_part} - {temp_title}"

    # Логика для строк без " - " (серии)
    temp_text = text
    has_changes_series = False
    for token in author_tokens:
        safe_token = re.escape(token)
        patterns = [
            rf'\[\s*{safe_token}\s*\]',
            rf'\(\s*{safe_token}\s*\)',
            rf'(?<!^)\b{safe_token}\b'
        ]
        for pattern in patterns:
            if re.search(pattern, temp_text, flags=re.IGNORECASE):
                temp_text = re.sub(pattern, ' ', temp_text, flags=re.IGNORECASE)
                has_changes_series = True

    if not has_changes_series:
        return text

    temp_text = re.sub(r'\s+', ' ', temp_text).strip(" .-")
    if not temp_text or (len(text) - len(temp_text) < min_limit):
        return text
    return temp_text[0].upper() + temp_text[1:] if temp_text else text
