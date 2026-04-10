from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from config import Config

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    csrf.init_app(app)

    # Flask-Login
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Пожалуйста, войдите в систему'
    login_manager.login_message_category = 'warning'

    from .models import User

    @login_manager.user_loader
    def load_user(user_id):
        user = User.query.get(int(user_id))
        # Если пользователь деактивирован — считаем его не залогиненным
        if user and not user.is_active_user:
            return None
        return user

    # Регистрируем blueprints
    from . import routes
    routes.init_app(app)

    from .auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from .admin import admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')

    # ── Вылет деактивированного пользователя при каждом запросе ──
    @app.before_request
    def check_user_active():
        from flask_login import current_user, logout_user
        from flask import redirect, url_for, flash
        if current_user.is_authenticated and not current_user.is_active_user:
            logout_user()
            flash('Ваш аккаунт деактивирован', 'error')
            return redirect(url_for('auth.login'))

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

    # ── Страницы ошибок ──
    @app.errorhandler(404)
    def not_found(e):
        from flask import render_template
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def server_error(e):
        from flask import render_template
        return render_template('errors/500.html'), 500

    return app
