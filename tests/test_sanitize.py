#-------------------------------------------------------------
# file: tests/test_sanitize.py
#-------------------------------------------------------------

import unittest
import sys
from pathlib import Path

# Добавляем корневую директорию проекта в пути поиска, чтобы импорты из src/ работали корректно
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.utils import sanitize_text_base


class TestSanitizeTextBase(unittest.TestCase):

    def test_sanitize_pure_russian(self):
        """Проверка, что чистая кириллица возвращается без изменений."""
        self.assertEqual(sanitize_text_base("Веселова Янина", base_lang="ru"), "Веселова Янина")

    def test_sanitize_leading_latin_twin(self):
        """Проверка выравнивания заглавной латинской 'A' в начале русского слова (Гладков Александр)."""
        # Первая буква 'A' здесь латинская (ASCII 65), остальные — русские
        dirty_input = "Гладков Aлександр Константинович"
        expected = "Гладков Александр Константинович"
        self.assertEqual(sanitize_text_base(dirty_input, base_lang="ru"), expected)

    def test_sanitize_embedded_latin_twin(self):
        """Проверка выравнивания строчной латинской 'o' внутри русского слова (Веселoва)."""
        # Буква 'o' на 6-й позиции здесь латинская (ASCII 111), остальные — русские
        dirty_input = "Веселoва Янина"
        expected = "Веселова Янина"
        self.assertEqual(sanitize_text_base(dirty_input, base_lang="ru"), expected)

    def test_sanitize_protect_english_words(self):
        """Проверка, что легитимные английские слова в русской строке не портятся трансляцией."""
        # Английское слово "Zero" должно остаться латиницей, а русские слова — очиститься
        dirty_input = "Давыдова - Культура Zero"
        self.assertEqual(sanitize_text_base(dirty_input, base_lang="ru"), "Давыдова - Культура Zero")


if __name__ == '__main__':
    unittest.main()
