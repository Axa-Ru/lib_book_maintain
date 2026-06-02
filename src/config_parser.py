import os
import tomllib
from pathlib import Path

def load_and_parse_config(config_path: str) -> dict:
    """
    Загружает TOML конфигурацию и автоматически подставляет
    значение src_base во все зависимые пути внутри секции [directories].
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Файл конфигурации не найден: {config_path}")

    with open(config_path, "rb") as f:
        config = tomllib.load(f)

    # Извлекаем базовый путь
    paths = config.get("paths", {})
    if paths["use_test"]:
        paths["src_base"] = paths["src_test_base"]
    else:
        paths["src_base"] = paths["src_prod_base"]

    src_base = paths["src_base"]

    if not src_base:
        raise KeyError("В секции [directories] отсутствует обязательный параметр 'src_base'")

    # 2. Модифицируем секцию [directories], делая все пути абсолютными
    dirs = config.get("directories", {})
    base_path_obj = Path(src_base)

    for key, value in dirs.items():
        if isinstance(value, str):
            # Создаем абсолютный путь: базовый_путь / относительный_путь
            # Метод as_posix() возвращает строку с правильными слэшами для Linux
            dirs[key] = (base_path_obj / value).as_posix()

    # если отсутствуют рабочие каталоги - создаем их
    if not dirs["zip_done"]:
        Path(dirs["zip_done"])
    if not dirs["fb2err"]:
        Path(dirs["fb2err"])

    return config
