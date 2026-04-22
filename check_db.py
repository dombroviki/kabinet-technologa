from app import create_app, db
from sqlalchemy import text

app = create_app()
with app.app_context():
    r = db.session.execute(text(
        "SELECT model, lot, sheet_row, sheet_gid FROM tv_model WHERE model='50UST5970' LIMIT 3"
    )).fetchall()
    print(r)
