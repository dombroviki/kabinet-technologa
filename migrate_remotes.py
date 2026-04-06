"""
Запуск: python migrate_remotes.py
Создаёт таблицу remote_control и добавляет начальные пульты.
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'instance', 'tv_models.db')

INITIAL_REMOTES = ['Hartens', 'JKT', 'Salute', 'Skyworth', 'KIVI']

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

try:
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS remote_control (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(100) UNIQUE NOT NULL
        )
    ''')
    print("✅ Таблица remote_control создана")

    added = 0
    for name in INITIAL_REMOTES:
        cursor.execute("SELECT id FROM remote_control WHERE name=?", (name,))
        if not cursor.fetchone():
            cursor.execute("INSERT INTO remote_control (name) VALUES (?)", (name,))
            added += 1

    conn.commit()
    print(f"✅ Добавлено {added} пультов: {', '.join(INITIAL_REMOTES)}")

except Exception as e:
    conn.rollback()
    print(f"❌ Ошибка: {e}")
finally:
    conn.close()
