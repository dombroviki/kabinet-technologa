"""
Запуск: python migrate_comments.py
Создаёт таблицу model_comment для комментариев к моделям.
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'instance', 'tv_models.db')

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

try:
    cur.execute('''
        CREATE TABLE IF NOT EXISTS model_comment (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            tv_model_id INTEGER NOT NULL REFERENCES tv_model(id) ON DELETE CASCADE,
            user_id     INTEGER REFERENCES user(id) ON DELETE SET NULL,
            text        TEXT NOT NULL,
            timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
        )
    ''')
    cur.execute('CREATE INDEX IF NOT EXISTS ix_comment_tv_model ON model_comment(tv_model_id)')
    conn.commit()
    print('✅ Таблица model_comment создана')
except Exception as e:
    conn.rollback()
    print(f'❌ Ошибка: {e}')
finally:
    conn.close()
