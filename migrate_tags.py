"""
Запуск: python migrate_tags.py
Создаёт таблицы tag и tv_model_tags.
"""
import sqlite3, os

DB_PATH = os.path.join(os.path.dirname(__file__), 'instance', 'tv_models.db')

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

try:
    cur.execute('''CREATE TABLE IF NOT EXISTS tag (
        id    INTEGER PRIMARY KEY AUTOINCREMENT,
        name  VARCHAR(100) UNIQUE NOT NULL,
        color VARCHAR(20)  NOT NULL DEFAULT '#4f8ef0'
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS tv_model_tags (
        tv_model_id INTEGER NOT NULL REFERENCES tv_model(id),
        tag_id      INTEGER NOT NULL REFERENCES tag(id),
        PRIMARY KEY (tv_model_id, tag_id)
    )''')

    conn.commit()
    print("✅ Таблицы tag и tv_model_tags созданы")

except Exception as e:
    conn.rollback()
    print(f"❌ Ошибка: {e}")
finally:
    conn.close()
