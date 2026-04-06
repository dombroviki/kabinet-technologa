from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import Config

db = SQLAlchemy()
login_manager = LoginManager()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)

    # Flask-Login
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Пожалуйста, войдите в систему'
    login_manager.login_message_category = 'warning'

    from .models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Регистрируем blueprints
    from . import routes
    routes.init_app(app)

    from .auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from .admin import admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')

    # Создаём таблицы если их нет
    with app.app_context():
        db.create_all()
        # Создаём первого админа если пользователей нет
        from .models import User
        if User.query.count() == 0:
            admin = User(
                email='doombrovskii@gmail.com',
                name='Домбровский Г.И.',
                role='admin',
                is_active_user=True
            )
            admin.set_password('horizonttest9')
            db.session.add(admin)
            db.session.commit()

    return app
