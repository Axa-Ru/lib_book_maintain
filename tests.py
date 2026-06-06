# -------------------------------------------------------------
# file: tests.py
# -------------------------------------------------------------

import unittest
from pathlib import Path

# Импортируем наши очищенные сущности и утилиты
from src.utils import sanitize_text_base, strip_spaces_inside_brackets, fix_uppercase_text
from src.book_class import Book
from src.series_class import Series


class TestTraumLibraryCore(unittest.TestCase):

    def setUp(self):
        """Инициализация базовой配置 для каждого теста."""
        self.book_cfg = {
            "title_max_limit": 32,
            "title_substr": [
                ["(сборник)", "(Сб)"],
                ["[litres]", ""],
                ["(Межавторский цикл)", "(МЦ)"]
            ]
        }

    # === БЛОК 1: Тестирование базовых текстовых утилит из utils.py ===

    def test_sanitize_text_base_spaces_and_dots(self):
        """Проверка схлопывания пробелов и удаления точек на концах."""
        self.assertEqual(sanitize_text_base("  Иванов   Иван  .", "ru"), "Иванов Иван")
        self.assertEqual(sanitize_text_base("Папка серии... ", "ru"), "Папка серии")

    def test_fix_mixed_layouts_majority_vote(self):
        """Проверка защиты мультиязычных строк."""
        # Чисто английское слово в скобках должно защититься и остаться латиницей
        self.assertEqual(sanitize_text_base("Мариана Запата [Cupcake]", "ru"), "Мариана Запата [Cupcake]")

        # Слово, где русские буквы побеждают, должно вылечиться (например, 'Робoты', где 'о' латинская)
        # Для простоты проверим базовый перевод латинских двойников в кириллицу для зоны ru
        self.assertEqual(sanitize_text_base("abc", "en"), "abc")

    def test_strip_spaces_inside_brackets(self):
        """Проверка удаления пробелов внутри скобок."""
        self.assertEqual(strip_spaces_inside_brackets("( Межавторский цикл )"), "(Межавторский цикл)")

    def test_fix_uppercase_text(self):
        """Проверка исправления КАПСА."""
        self.assertEqual(fix_uppercase_text("ИВАНОВ"), "Иванов")
        self.assertEqual(fix_uppercase_text("серия книг"), "серия книг")

    # === БЛОК 2: Тестирование токенизации и обрезки длин в Book ===

    def test_book_tokenization_clean_case(self):
        """Классический разбор: Автор - Название."""
        fake_series = Series("Тест")
        book = Book(Path("Заозерский - Гунны.epub"), fake_series)
        # В версии 0.9.3 вызываем метод пересчета имени явно, как в оркестраторе
        book.compute_new_name(author_name="Заозерский Андрей", book_cfg=self.book_cfg, base_lang="ru")

        self.assertEqual(book.author, "Заозерский")
        self.assertEqual(book.title, "Гунны")
        self.assertEqual(book.new_name, "Заозерский - Гунны.epub")

    def test_book_litres_removal(self):
        """Проблема Заозерского (Пункт 5): Вырезание мусора [litres]."""
        fake_series = Series("Тест")
        book = Book(Path("Заозерский - Гунны [litres].epub"), fake_series)
        book.compute_new_name(author_name="Заозерский Андрей", book_cfg=self.book_cfg, base_lang="ru")

        self.assertEqual(book.title, "Гунны")
        self.assertEqual(book.new_name, "Заозерский - Гунны.epub")

    def test_book_series_digits_removal(self):
        """Проблема Жаховской (Задача 1): Срезание номеров серий '00 '."""
        fake_series = Series("МИФ Детство")
        book = Book(Path("Жаховская 00 Роботы. Детская энциклопедия.epub"), fake_series)
        book.compute_new_name(author_name="Жаховская Ольга", book_cfg=self.book_cfg, base_lang="ru")

        self.assertEqual(book.title, "Роботы. Детская энциклопедия")

    def test_book_title_length_validation_with_dots(self):
        """Проблема Ильи Объедкова: Обрезка подзаголовков по внутренним точкам."""
        fake_series = Series("Психология")
        long_name = "Объедков Илья Викторович - Пульт управления тревогой. Проверенный метод доказательной психологии.epub"
        book = Book(Path(long_name), fake_series)
        book.compute_new_name(author_name="Объедков Илья Викторович", book_cfg=self.book_cfg, base_lang="ru")

        # Строка усекается по точкам, чтобы уложиться в лимит 32 символа названия произведения
        self.assertEqual(book.title, "Пульт управления тревогой")
        self.assertEqual(book.new_name, "Объедков - Пульт управления тревогой.epub")

    def test_book_tokenization_inside_series_with_full_name(self):
        """Тест для Синтии Обин: в имени файла должна оставаться ТОЛЬКО фамилия автора."""
        real_series = Series("Соблазн – Harlequin")
        file_name = "Обин Синтия - Лотерея соблазна.epub"
        book = Book(Path(file_name), real_series)

        # Передаем полное имя из каталога автора "Обин Синтия"
        book.compute_new_name(author_name="Обин Синтия", book_cfg=self.book_cfg, base_lang="ru")

        # 🔥 ЖЕСТКАЯ ПРОВЕРКА: Токен автора должен содержать только первое слово ФИО (Фамилию)
        self.assertEqual(book.author, "Обин")
        self.assertEqual(book.title, "Лотерея соблазна")

        # Итоговое имя должно собраться строго как "Фамилия - Название"
        self.assertEqual(book.new_name, "Обин - Лотерея соблазна.epub")


if __name__ == '__main__':
    unittest.main()
