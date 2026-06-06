# -------------------------------------------------------------
# module: src/book_class.py
# -------------------------------------------------------------

import re
from pathlib import Path
from src.utils import sanitize_text_base


class Book:
    """
    [Версия 0.9.3] Класс, описывающий конкретную книгу.
    Хранит физические параметры файла на диске и управляет его целевым состоянием (new_name).
    """

    def __init__(self, file_path: Path, series):
        self.path = file_path
        self.series = series
        self.name = file_path.name
        self.new_name = file_path.name

        self.author = ""
        self.series_index = ""  # Порядковый номер тома в серии (например, "00")
        self.title = file_path.stem
        self.tags = set()

    def _parse_stem_to_tokens(self, clean_stem: str, author_name: str, book_cfg: dict):
        """
        Точная токенизация стемма книги на основе переданного имени автора.
        Защищена от зацикливания и ложного захвата цифр из конца строки.
        """
        replacements = book_cfg.get("title_substr", [])
        self.tags.clear()

        # 1. Извлекаем семантические теги из TOML
        working_text = clean_stem
        for old_value, new_value in replacements:
            if old_value.lower() in working_text.lower():
                if new_value.strip("()[] ").lower():
                    self.tags.add(new_value.strip("()[] "))
                working_text = re.sub(re.escape(old_value), "", working_text, flags=re.IGNORECASE)

        working_text = re.sub(r'\[\s*\]|\(\s*\)', '', working_text)
        working_text = re.sub(r'\s+', ' ', working_text).strip()

        # Нормализуем любые виды тире/дефисов (—, –, -) в стандартный сепаратор " - "
        working_text = re.sub(r'\s*[–—_\\\-]+\s*', ' - ', working_text)
        working_text = re.sub(r'\s+', ' ', working_text).strip()

        # Фиксируем в качестве автора для имени файла ТОЛЬКО Фамилию (первое слово)
        if author_name:
            author_parts = [p for p in re.split(r'[.\s]+', author_name.strip()) if p]
            self.author = author_parts[0] if author_parts else author_name.strip()
        else:
            self.author = author_name.strip()

        # 🔥 ИСПРАВЛЕНО: Извлекаем индекс серии из ГРЯЗНОЙ строки до деления по дефисам!
        # Номер серии ищется как отдельно стоящие цифры (например, "00 " или "- 00 ")
        self.series_index = ""
        index_match = re.search(r'(?:^|\s|[-–—])(\d{2,3})(?:\s|[-–—]|$)', working_text)
        if index_match:
            self.series_index = index_match.group(1)
            # Вырезаем найденный индекс серии, чтобы он не мешал названию книги
            working_text = working_text.replace(index_match.group(0), ' - ')
            working_text = re.sub(r'\s+', ' ', working_text).strip()

        # 2. Изолируем название произведения (правую часть)
        if " - " in working_text:
            parts = working_text.split(" - ")
            # Ищем часть, которая не является автором
            title_parts = [p.strip() for p in parts if p.strip().lower() != self.author.lower() and p.strip()]
            raw_title = " - ".join(title_parts) if title_parts else working_text
        else:
            raw_title = working_text

        # 3. Вырезаем дубликаты слов автора из названия произведения (Пункт 7)
        author_tokens = [w.lower() for w in re.split(r'[.\s]+', author_name.strip()) if len(w) > 1]
        words = raw_title.split()
        clean_title_words = []

        for word in words:
            clean_word = word.strip(".,()[]- ").lower()
            if clean_word in author_tokens:
                continue
            clean_title_words.append(word)

        raw_title = " ".join(clean_title_words).strip(" .-")

        # Сохраняем чистый заголовок произведения
        self.title = raw_title.strip(" .-")

        # Восстанавливаем заглавную букву названия
        if self.title:
            self.title = self.title.upper()[0] + self.title[1:] if len(self.title) > 1 else self.title.upper()

    def validate_title_length(self, book_cfg: dict):
        """
        [Версия 0.9.3] 🔥 ИСПРАВЛЕНО: Метод физически внедрен в тело класса!
        Усекает сверхдлинные подзаголовки по точкам или по целым словам.
        """
        if not self.title:
            return

        max_limit = book_cfg.get("title_max_limit", 32)
        if len(self.title) <= max_limit:
            return

        # Вариант 1: Обрезка по внутренним точкам подзаголовков
        if "." in self.title:
            title_stripped = self.title.rstrip(" .")
            last_dot_idx = title_stripped.rfind(".")
            if last_dot_idx != -1:
                self.title = self.title[:last_dot_idx].strip(" .-")
                self.validate_title_length(book_cfg)  # Рекурсивно проверяем лимит снова
                return

        # Вариант 2: Обрезка по границам целых слов
        if len(self.title) > max_limit:
            words = self.title.split()
            current_parts = []
            for word in words:
                test_title = " ".join(current_parts + [word])
                if len(test_title) <= max_limit:
                    current_parts.append(word)
                else:
                    break

            if not current_parts and words:
                self.title = words[0][:max_limit].strip(" .-")
            else:
                self.title = " ".join(current_parts).strip(" .-")

        if self.title:
            self.title = self.title.upper()[0] + self.title[1:] if len(self.title) > 1 else self.title.upper()

    def compute_new_name(self, author_name: str, book_cfg: dict, base_lang: str = "ru"):
        """
        Вычисляет идеальное имя файла книги, принимая имя автора каталога явно.
        """
        raw_stem = self.path.stem
        clean_stem = sanitize_text_base(raw_stem, base_lang=base_lang)

        # 1. Разбираем стемм на изолированные токены
        self._parse_stem_to_tokens(clean_stem, author_name, book_cfg)

        # 2. Жестко усекаем длину названия ДО сборки результирующей строки
        self.validate_title_length(book_cfg)

        # 3. Собираем идеальное имя файла обратно по вашему стандарту
        if self.author and self.title:
            # Книга лежит в реальной серии и у нее обнаружен номер тома
            if self.series and not self.series.is_virtual and self.series_index:
                stem_result = f"{self.author} {self.series_index} {self.title}"
            else:
                # Одиночная книга в корне автора (индекс серии полностью игнорируется)
                stem_result = f"{self.author} - {self.title}"
        else:
            stem_result = self.title if self.title else clean_stem

        # Приклеиваем семантические теги
        if self.tags:
            sorted_tags = sorted(list(self.tags))
            tags_string = " ".join(f"({tag})" for tag in sorted_tags)
            stem_result = f"{stem_result} {tags_string}"

        self.new_name = f"{stem_result}.epub"

    def is_same_as(self, other_book: 'Book') -> bool:
        """Проверяет совпадение книг на основе строгого сравнения их чистых title."""
        if not self.title or not other_book.title:
            return False
        return self.title.lower().strip() == other_book.title.lower().strip()

    def compare_with(self, other_book_path: Path) -> int:
        """Сравнивает текущую книгу по размеру с другим файлом на диске."""
        try:
            size_self = self.path.stat().st_size
            size_other = other_book_path.stat().st_size
        except OSError:
            return 0

        if size_self > size_other:
            return 1
        elif size_other > size_self:
            return 2
        return 0
