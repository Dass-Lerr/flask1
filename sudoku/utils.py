import json
import os


def save_json(folder: str, filename: str, data) -> None:
    """Сохраняет данные в JSON-файл по пути folder/filename."""
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_json(folder: str, filename: str):
    """Загружает и возвращает данные из JSON-файла по пути folder/filename."""
    path = os.path.join(folder, filename)
    with open(path, encoding="utf-8") as f:
        return json.load(f)
