"""
Запуск: python migrate_sw.py
Добавляет колонку software_version в таблицу tv_model.
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'instance', 'tv_models.db')

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE tv_model ADD COLUMN software_version VARCHAR(100)")
    conn.commit()
    print("✅ Колонка software_version успешно добавлена в таблицу tv_model")
except sqlite3.OperationalError as e:
    if 'duplicate column name' in str(e):
        print("⚠️  Колонка software_version уже существует — ничего не изменилось")
    else:
        print(f"❌ Ошибка: {e}")
finally:
    conn.close()
