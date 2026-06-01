"""
Запусти этот скрипт ОДИН РАЗ из папки проекта:
    python migrate_db.py

Он добавит недостающие колонки в существующую базу данных
без потери данных.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "instance", "sudoku.db")

# Flask по умолчанию кладёт SQLite в папку instance/
# Если у тебя база лежит рядом с app.py — поменяй путь:
# DB_PATH = os.path.join(os.path.dirname(__file__), "sudoku.db")

def column_exists(cursor, table, column):
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"База данных не найдена по пути: {DB_PATH}")
        print("Попробуй изменить DB_PATH в начале скрипта.")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    migrations = [
        ("users", "is_admin",      "INTEGER NOT NULL DEFAULT 0"),
        ("users", "bio",           "TEXT"),
        ("users", "avatar_color",  "TEXT"),
        ("users", "registered_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
    ]

    for table, col, col_def in migrations:
        if not column_exists(cur, table, col):
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_def}")
            print(f"  + добавлена колонка {table}.{col}")
        else:
            print(f"  ✓ {table}.{col} уже существует")

    conn.commit()
    conn.close()
    print("\nМиграция завершена. Теперь запускай python app.py")

if __name__ == "__main__":
    migrate()
