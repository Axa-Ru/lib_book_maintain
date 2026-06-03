# -----------------------------------------------------------------------
# file: utils.py
# Утилиты
# -----------------------------------------------------------------------
import re


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


# Словарь соответствия: слева кириллица, справа латиница
_CYR_TO_LAT = str.maketrans({
    'А': 'A', 'В': 'B', 'Е': 'E', 'Н': 'H', 'К': 'K', 'М': 'M',
    'О': 'O', 'Р': 'P', 'С': 'C', 'Т': 'T', 'Х': 'X',
    'а': 'a', 'е': 'e', 'о': 'o', 'р': 'p', 'с': 'c', 'х': 'x'
})

# Словарь соответствия: слева латиница, справа кириллица
_LAT_TO_CYR = str.maketrans({
    'A': 'А', 'B': 'В', 'E': 'Е', 'H': 'Н', 'K': 'К', 'M': 'М',
    'O': 'О', 'P': 'Р', 'C': 'С', 'T': 'Т', 'X': 'Х',
    'a': 'а', 'e': 'е', 'o': 'о', 'p': 'р', 'c': 'с', 'x': 'х'
})


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


import logging


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
