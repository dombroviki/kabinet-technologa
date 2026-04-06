"""
Запуск: python migrate_firmware.py
Создаёт таблицу tv_model_firmware и переносит существующие прошивки из tv_model.firmware_filename
"""
import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'instance', 'tv_models.db')

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

try:
    # Создаём новую таблицу
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tv_model_firmware (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tv_model_id INTEGER NOT NULL REFERENCES tv_model(id),
            filename VARCHAR(200) NOT NULL,
            original_name VARCHAR(200) NOT NULL,
            uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    print("✅ Таблица tv_model_firmware создана")

    # Переносим существующие прошивки
    cursor.execute("SELECT id, firmware_filename FROM tv_model WHERE firmware_filename IS NOT NULL AND firmware_filename != ''")
    rows = cursor.fetchall()
    migrated = 0
    for tv_id, fname in rows:
        # Проверяем что запись ещё не перенесена
        cursor.execute("SELECT id FROM tv_model_firmware WHERE tv_model_id=? AND filename=?", (tv_id, fname))
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO tv_model_firmware (tv_model_id, filename, original_name, uploaded_at) VALUES (?, ?, ?, ?)",
                (tv_id, fname, fname, datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'))
            )
            migrated += 1

    conn.commit()
    if migrated:
        print(f"✅ Перенесено {migrated} прошивок из старой структуры")
    else:
        print("ℹ️  Нет прошивок для переноса (уже перенесены или их не было)")

except Exception as e:
    conn.rollback()
    print(f"❌ Ошибка: {e}")
finally:
    conn.close()
