# -------------------------------------------------------------
# file: tests/test_author.py
# -------------------------------------------------------------

import unittest
import sys
import tempfile
from pathlib import Path

# Добавляем корневую директорию проекта в пути поиска, чтобы импорты из src/ работали корректно
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.author_class import Author
from src.series_class import Series
from src.book_class import Book


class TestAuthorClass(unittest.TestCase):

    def setUp(self):
        """Инициализация базовой конфигурации перед каждым тестом."""
        self.global_config = {
            "series": {
                "compare_ratio": 81
            }
        }
        self.book_cfg = {
            "title_max_limit": 32,
            "title_substr": []
        }

    def test_author_initialization_raw_name(self):
        """Проверка, что конструктор сохраняет имя папки с диска абсолютно нетронутым."""
        author_path = Path("/tmp/#library/ru/З/Заозерский Андрей")
        author = Author(author_path)

        self.assertEqual(author.name, "Заозерский Андрей")
        self.assertEqual(author.new_name, "Заозерский Андрей")

    def test_compare_name_author_barrier_logic(self):
        """Проверка работы изолированного приватного лингвистического барьера _compare_name_author."""
        author_base = Author(Path("Ибрагимова Диана Маратовна"))
        author_base.compute_new_name(base_lang="ru")

        # 1. Совместимый кейс: Отчество отсутствует у второго
        author_no_paternal = Author(Path("Ибрагимова Диана"))
        author_no_paternal.compute_new_name(base_lang="ru")
        self.assertTrue(author_base._compare_name_author(author_no_paternal))

        # 2. Совместимый кейс: Отчество указано инициалом
        author_initial = Author(Path("Ибрагимова Диана М."))
        author_initial.compute_new_name(base_lang="ru")
        self.assertTrue(author_base._compare_name_author(author_initial))

        # 3. НЕсовместимый кейс: Разные имена (Иван и Петр) — защита тезок
        author_ivan = Author(Path("Иванов Иван"))
        author_ivan.compute_new_name(base_lang="ru")
        author_petr = Author(Path("Иванов Петр"))
        author_petr.compute_new_name(base_lang="ru")
        self.assertFalse(author_ivan._compare_name_author(author_petr))

        # 4. НЕсовместимый кейс: Разные отчества при одинаковых именах
        author_marat = Author(Path("Ибрагимова Диана Маратовна"))
        author_marat.compute_new_name(base_lang="ru")
        author_ivanovna = Author(Path("Ибрагимова Диана Ивановна"))
        author_ivanovna.compute_new_name(base_lang="ru")
        self.assertFalse(author_marat._compare_name_author(author_ivanovna))

    def test_is_same_as_cascading_with_series_match(self):
        """Проверка Шага 3 (Кейс Ибрагимовой): Слияние по совпадению редкой серии при совместимых ФИО."""
        author_a = Author(Path("Ибрагимова Диана"))
        author_b = Author(Path("Ибрагимова Диана Маратовна"))
        author_a.compute_new_name(base_lang="ru")
        author_b.compute_new_name(base_lang="ru")

        # Создаем одноименные папки серий в памяти объектов
        series_a = Series("Сетерра")
        series_b = Series("Сетерра")

        author_a.series_list = [author_a.virtual_series, series_a]
        author_b.series_list = [author_b.virtual_series, series_b]

        # Метод ОБЯЗАН выдать True (ФИО совместимы, названия серий совпали)
        self.assertTrue(author_a.is_same_as(author_b, self.global_config))

    def test_is_same_as_cascading_with_books_match(self):
        """Проверка Шага 4: Слияние по совпадению книги, если папки серий не пересеклись."""
        author_a = Author(Path("Житинский Александр"))
        author_b = Author(Path("Житинский А."))
        author_a.compute_new_name(base_lang="ru")
        author_b.compute_new_name(base_lang="ru")

        # Разные папки серий на диске (названия не пересекаются)
        series_a = Series("Настоящий американец")
        series_b = Series("Повести разных лет")

        # Создаем книги в памяти объектов
        book_a = Book(Path("Житинский - Потерянный дом.epub"), author_a.virtual_series)
        book_b = Book(Path("Житинский - Потерянный дом [litres].epub"), series_b)

        # 🔥 ЖЕСТКО ФИКСИРУЕМ ОДИНАКОВЫЙ TITLE, ЧТОБЫ ТЕСТИРОВАТЬ ИМЕННО КАСКАД АВТОРА
        book_a.title = "Потерянный дом"
        book_b.title = "Потерянный дом"

        # Наполняем книги в структуры серий
        author_a.virtual_series.books = [book_a]
        series_b.books = [book_b]

        # Линкуем серии к авторам
        author_a.series_list = [author_a.virtual_series, series_a]
        author_b.series_list = [author_b.virtual_series, series_b]

        # Метод ОБЯЗАН выдать True, так как каскад дойдет до перекрестной проверки книг!
        self.assertTrue(author_a.is_same_as(author_b, self.global_config))


    def test_author_physical_join_with(self):
        """Проверка Шага 5: Физический перенос и поглощение каталогов на уровне ОС."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_path = Path(tmp_dir)

            dir_secondary = base_path / "Журавлёв Михаил"
            dir_primary = base_path / "Журавлев Михаил Георгиевич"
            dir_secondary.mkdir()
            dir_primary.mkdir()

            series_unique_path = dir_secondary / "Уникальная Серия"
            series_conflict_path_a = dir_secondary / "Общая Серия"
            series_unique_path.mkdir()
            series_conflict_path_a.mkdir()

            series_conflict_path_b = dir_primary / "Общая Серия"
            series_conflict_path_b.mkdir()

            book_unique = series_unique_path / "Журавлев - Книга 1.epub"
            book_unique.write_text("Unique Book Data")

            book_conflict_small = series_conflict_path_a / "Журавлев - Книга 2.epub"
            book_conflict_small.write_text("Small")

            book_conflict_large = series_conflict_path_b / "Журавлев - Книга 2.epub"
            book_conflict_large.write_text("Much Larger Content Data")

            author_secondary = Author(dir_secondary)
            author_primary = Author(dir_primary)

            s_unique = Series(name="Уникальная Серия")
            s_conflict_a = Series(name="Общая Серия")
            s_conflict_b = Series(name="Общая Серия")

            s_unique.books = [Book(book_unique, s_unique)]
            s_conflict_a.books = [Book(book_conflict_small, s_conflict_a)]
            s_conflict_b.books = [Book(book_conflict_large, s_conflict_b)]

            author_secondary.series_list = [author_secondary.virtual_series, s_unique, s_conflict_a]
            author_primary.series_list = [author_primary.virtual_series, s_conflict_b]

            success = author_secondary.join_with(author_primary)

            self.assertTrue(success)
            self.assertFalse(dir_secondary.exists())
            self.assertTrue(dir_primary.exists())

    def test_author_with_apostrophe_normalization(self):
        """Кейс 1: Проверка приведения разнородных апострофов к единому машинному стандарту."""
        author = Author(Path("О’Генри"))
        author.compute_new_name(base_lang="ru")

        # 🔥 Теперь ожидаем строгий машинный апостроф и заглавную Г
        self.assertEqual(author.new_name, "О'Генри")

    def test_author_with_foreign_prefixes(self):
        """Кейс 2: Проверка склеивания иностранных приставок (де, фон, ван) через дефис."""
        author = Author(Path("де биржерак сирано"))
        author.compute_new_name(base_lang="ru")

        # 🔥 Теперь ожидаем строго наш стандарт 'де-Биржерак'
        self.assertEqual(author.new_name, "де-Биржерак Сирано")

    def test_author_with_acute_accent_normalization(self):
        """Кейс 1.5: Проверка приведения знака острого ударения ´ к машинному апострофу '."""
        # Симулируем имя автора со знаком острого ударения ´ в фамилии
        author = Author(Path("Д´Айн"))
        author.compute_new_name(base_lang="ru")

        # На выходе ожидаем строгий машинный апостроф ' и заглавную букву после него
        self.assertEqual(author.new_name, "Д'Айн")


if __name__ == '__main__':
    unittest.main()
