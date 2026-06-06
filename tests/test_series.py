# -------------------------------------------------------------
# file: tests/test_series.py
# -------------------------------------------------------------

import unittest
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.series_class import Series


class TestSeriesClass(unittest.TestCase):

    def setUp(self):
        """Инициализация конфигурации TOML для нечеткого сравнения серий."""
        self.global_config = {
            "series": {
                "compare_ratio": 81
            }
        }
        self.replaces = {
            "(Межавторский цикл)": "(мц)",
            "[litres]": ""
        }

    def test_virtual_series_property(self):
        """Проверка флага виртуальности для одиночных книг."""
        v_series = Series(name="")
        self.assertTrue(v_series.is_virtual)
        self.assertEqual(v_series.name, "")

        r_series = Series(name="МИФ Детство")
        self.assertFalse(r_series.is_virtual)

    def test_series_sanitize_name(self):
        """Проверка базовой очистки подстрок мусора из конфигурации."""
        series = Series("S.T.A.L.K.E.R. (Межавторский цикл)")
        clean_res = series.sanitize_name(self.replaces)
        self.assertIn("(мц)", clean_res)

    def test_series_compute_new_name(self):
        """Проверка полной цепочки формирования new_name для серии."""
        series = Series("мир фантастики [litres]")
        series.compute_new_name(replaces=self.replaces, author_name="Иванов", base_lang="ru")

        # Ожидаем исправление регистра (первая заглавная) и удаление [litres]
        self.assertEqual(series.new_name, "Мир фантастики")

    def test_is_same_as_fuzzy_matching(self):
        """Проверка нечеткого сопоставления похожих папок серий по коэффициенту."""
        series_a = Series("Сага Содружества")
        series_a.compute_new_name(replaces=self.replaces, author_name="Гамильтон", base_lang="ru")

        series_b = Series("Сага о Содружестве")
        series_b.compute_new_name(replaces=self.replaces, author_name="Гамильтон", base_lang="ru")

        # Из-за высокого token_set_ratio метод должен признать их дубликатами
        self.assertTrue(series_a.is_same_as(series_b, self.global_config))

    def test_series_physical_join_with(self):
        """
        [Версия 0.9.3] Тест физического слияния папок серий.
        Проверяет перенос уникальных книг, дуэль размеров и удаление опустевшей папки.
        """
        import tempfile
        import shutil
        from src.book_class import Book

        # 1. Создаем изолированную временную среду на диске (внутри /tmp)
        with tempfile.TemporaryDirectory() as tmp_dir:
            author_folder = Path(tmp_dir) / "Гамильтон Питер"
            author_folder.mkdir()

            # Создаем физические папки двух похожих серий
            dir_a = author_folder / "Сага о Содружестве"  # (Второстепенная - будет удалена)
            dir_b = author_folder / "Сага Содружества"  # (Главная - поглотит серию А)
            dir_a.mkdir()
            dir_b.mkdir()

            # 2. Наполняем папки файлами книг для симуляции дуэли размеров
            # Книга 1: Есть только в серии А (должна успешно переместиться в серию Б)
            book1_path = dir_a / "Гамильтон - Звезда Пандоры.epub"
            book1_path.write_text("Unique content of book 1")  # Имитируем файл

            # Книга 2: Конфликт имен! В серии А файл МЕНЬШЕ, в серии Б — БОЛЬШЕ
            book2_path_small = dir_a / "Гамильтон - Иуда освобожденный.epub"
            book2_path_small.write_text("Small")  # Худшая копия

            book2_path_large = dir_b / "Гамильтон - Иуда освобожденный.epub"
            book2_path_large.write_text("Much Larger Content")  # Лучшая копия (должна выжить)

            # 3. Инициализируем ООП-объекты серий и книг в памяти
            series_a = Series(name="Сага о Содружестве")
            series_b = Series(name="Сага Содружества")

            # Создаем объекты книг и привязываем их к путям на диске
            book1 = Book(book1_path, series_a)
            book2_small = Book(book2_path_small, series_a)

            series_a.books = [book1, book2_small]
            series_b.books = [Book(book2_path_large, series_b)]

            # 4. ДЕЙСТВИЕ: Серия А физически поглощается Серией Б
            success = series_a.join_with(series_b, author_folder)

            # 5. ПРОВЕРКИ (ASSERTIONS):
            self.assertTrue(success, "Метод join_with должен вернуть True при успешном слиянии")

            # Проверяем дисковую структуру после слияния
            self.assertFalse(dir_a.exists(), "Исходная папка серии А должна быть физически удалена с диска")
            self.assertTrue(dir_b.exists(), "Целевая папка серии Б должна остаться на диске")

            # Проверяем физический перенос уникального файла
            expected_book1_path = dir_b / "Гамильтон - Звезда Пандоры.epub"
            self.assertTrue(expected_book1_path.is_file(),
                            "Уникальная книга 1 должна физически переехать в папку серии Б")

            # Проверяем исход дуэли размеров конфликтующего файла
            self.assertTrue(book2_path_large.is_file(), "Файл большего размера в целевой серии должен выжить")
            self.assertEqual(
                book2_path_large.stat().st_size, len("Much Larger Content"),
                "Размер выжившего файла должен соответствовать лучшей копии"
            )


if __name__ == '__main__':
    unittest.main()
