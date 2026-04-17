"""
Миграция: добавляет колонки sheet_row и sheet_gid в таблицу tv_model.
Запуск: python run_migration.py (из корня проекта, локально)
"""
from app import create_app, db
from sqlalchemy import text

app = create_app()
with app.app_context():
    with db.engine.connect() as conn:
        for col, typ in [('sheet_row', 'INTEGER'), ('sheet_gid', 'INTEGER')]:
            try:
                conn.execute(text(f"ALTER TABLE tv_model ADD COLUMN {col} {typ}"))
                print(f"✅ {col} добавлен")
            except Exception as e:
                print(f"⚠️  {col}: {e}")
        conn.commit()
    print("Готово.")
