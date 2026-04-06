from app import create_app, db
from app.models import Brand, LauncherType

app = create_app()

with app.app_context():
    db.create_all()

    # Бренды
    brands = ['Samsung', 'LG', 'Sony', 'Philips', 'Hisense', 'TCL', 'Haier']
    for name in brands:
        if not Brand.query.filter_by(name=name).first():
            db.session.add(Brand(name=name))

    # Типы лаунчеров
    launchers = ['Tizen', 'WebOS', 'Android TV', 'Google TV', 'Roku', 'собственный']
    for name in launchers:
        if not LauncherType.query.filter_by(name=name).first():
            db.session.add(LauncherType(name=name))

    db.session.commit()
    print('База данных заполнена!')
