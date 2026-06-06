# -------------------------------------------------------------
# file: tests/test_book.py
# -------------------------------------------------------------

import unittest
import sys
from pathlib import Path

# Добавляем корневую директорию в пути поиска модулей, чтобы импорты из src/ работали корректно
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.book_class import Book
from src.series_class import Series


class TestBookClass(unittest.TestCase):

    def setUp(self):
        """Инициализация эталонной конфигурации перед каждым тестом."""
        self.book_cfg = {
            "title_max_limit": 32,
            "title_substr": [
                ["(сборник)", "(Сб)"],
                ["[litres]", ""],
                ["(Межавторский цикл)", "(МЦ)"]
            ]
        }
        self.fake_series = Series("Тестовая Серия")

    def test_initialization_state(self):
        """Проверка корректности базового конструктора книги."""
        file_path = Path("Иванов - Чистый заголовок.epub")
        book = Book(file_path, self.fake_series)

        self.assertEqual(book.name, "Иванов - Чистый заголовок.epub")
        self.assertEqual(book.new_name, "Иванов - Чистый заголовок.epub")
        self.assertEqual(book.author, "")

    def test_standard_tokenization(self):
        """Проверка стандартного разбора 'Автор - Название'."""
        book = Book(Path("Заозерский - Гунны.epub"), self.fake_series)
        book.compute_new_name(author_name="Заозерский Андрей", book_cfg=self.book_cfg, base_lang="ru")

        self.assertEqual(book.author, "Заозерский")
        self.assertEqual(book.title, "Гунны")
        self.assertEqual(book.new_name, "Заозерский - Гунны.epub")

    def test_cleaning_garbage_tags(self):
        """Проверка динамического вырезания тегов вроде [litres]."""
        book = Book(Path("Заозерский - Гунны [litres].epub"), self.fake_series)
        book.compute_new_name(author_name="Заозерский Андрей", book_cfg=self.book_cfg, base_lang="ru")

        self.assertEqual(book.title, "Гунны")
        self.assertEqual(book.new_name, "Заозерский - Гунны.epub")

    def test_series_digits_stripping(self):
        """Проблема Жаховской (Задача 1): Срезание номеров серий '00 '."""
        fake_series = Series("МИФ Детство")
        book = Book(Path("Жаховская 00 Роботы. Детская энциклопедия.epub"), fake_series)
        book.compute_new_name(author_name="Жаховская Ольга", book_cfg=self.book_cfg, base_lang="ru")

        self.assertEqual(book.author, "Жаховская")
        self.assertEqual(book.title, "Роботы. Детская энциклопедия")
        self.assertEqual(book.series_index, "00")

        # 🔥 ИСПРАВЛЕНО под ваш финальный стандарт серий (без дефиса перед 00):
        self.assertEqual(book.new_name, "Жаховская 00 Роботы. Детская энциклопедия.epub")

    def test_title_truncation_by_dots(self):
        """Проверка рекурсивного усечения подзаголовков по точкам (Проблема Объедкова)."""
        long_name = "Объедков Илья Викторович - Пульт управления тревогой. Проверенный метод доказательной психологии.epub"
        book = Book(Path(long_name), self.fake_series)
        book.compute_new_name(author_name="Объедков Илья Викторович", book_cfg=self.book_cfg, base_lang="ru")

        self.assertEqual(book.title, "Пульт управления тревогой")
        self.assertEqual(book.new_name, "Объедков - Пульт управления тревогой.epub")

    def test_title_truncation_by_words(self):
        """Проверка усечения по границам целых слов при отсутствии точек."""
        long_name = "Автор - Длинное название книги без точек для проверки отсечения слов.epub"
        book = Book(Path(long_name), self.fake_series)
        book.compute_new_name(author_name="Автор Папки", book_cfg=self.book_cfg, base_lang="ru")

        # Длина title не должна превышать лимит 32 символа, слова не должны быть обрублены
        self.assertTrue(len(book.title) <= 32)
        self.assertTrue(book.title.startswith("Длинное название"))

    def test_is_same_as_logic(self):
        """Проверка ООП-метода сопоставления идентичности произведений."""
        book_a = Book(Path("Обин - Лотерея соблазна.epub"), self.fake_series)
        book_a.compute_new_name(author_name="Обин Синтия", book_cfg=self.book_cfg, base_lang="ru")

        book_b = Book(Path("Обин Синтия - Лотерея соблазна.epub"), self.fake_series)
        book_b.compute_new_name(author_name="Обин Синтия", book_cfg=self.book_cfg, base_lang="ru")

        self.assertTrue(book_a.is_same_as(book_b))

    def test_book_series_index_extraction_inside_series(self):
        """Проверка выделения номера тома для книги, лежащей внутри реальной серии."""
        # Книга лежит в реальной серии "Досье"
        real_series = Series("Досье")
        file_name = "Дамаскин 00 Разведчицы и шпионки - 2.epub"
        book = Book(Path(file_name), real_series)

        # Пересчитываем имя
        book.compute_new_name(author_name="Дамаскин Игорь Анатольевич", book_cfg=self.book_cfg, base_lang="ru")

        # ПРОВЕРКИ:
        self.assertEqual(book.series_index, "00")  # Номер серии должен успешно сохраниться в памяти
        self.assertEqual(book.title, "Разведчицы и шпионки - 2")  # Чистый title не должен содержать индекс серии

        # Финальное имя должно собраться строго по утвержденному эталону (без дефиса перед цифрами)
        self.assertEqual(book.new_name, "Дамаскин 00 Разведчицы и шпионки - 2.epub")

    def test_book_series_index_ignored_in_virtual_series(self):
        """Проверка, что для одиночных книг из корня автора номер серии игнорируется."""
        # Книга лежит в виртуальной серии (корень автора)
        virtual_series = Series("")
        file_name = "Дамаскин 00 Разведчицы и шпионки - 2.epub"
        book = Book(Path(file_name), virtual_series)

        book.compute_new_name(author_name="Дамаскин Игорь Анатольевич", book_cfg=self.book_cfg, base_lang="ru")

        # ПРОВЕРКА: Поскольку серии нет, префикс "00" не должен подставляться в имя файла корня
        self.assertEqual(book.new_name, "Дамаскин - Разведчицы и шпионки - 2.epub")


if __name__ == '__main__':
    unittest.main()
