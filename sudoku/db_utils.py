"""
JSON-based storage helpers.
Taken from lab work and adapted for sudoku project.
"""

import json
import os
from threading import Lock

_lock = Lock()


def read_json(path: str, default=None):
    """Read JSON file, return default if missing or corrupt."""
    if default is None:
        default = {}
    with _lock:
        if not os.path.exists(path):
            return default
        with open(path, encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return default


def write_json(path: str, data) -> None:
    """Write data to JSON file atomically."""
    with _lock:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
