from flask import Blueprint, render_template, redirect, url_for, request, flash, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from . import db
from .models import User
import requests
import urllib.parse
import secrets

auth_bp = Blueprint('auth', __name__)

# ──────────────────────────────────────────────
#  Вход по логину/паролю
# ──────────────────────────────────────────────

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))

        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            flash('Неверный email или пароль', 'error')
            return render_template('auth/login.html')

        if not user.is_active_user:
            flash('Ваш аккаунт деактивирован', 'error')
            return render_template('auth/login.html')

        login_user(user, remember=remember)
        try:
            from creds import save_credentials
            save_credentials(email, password)
        except Exception:
            pass
        next_page = request.args.get('next')
        return redirect(next_page or url_for('index'))

    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    try:
        from creds import clear_credentials
        clear_credentials()
    except Exception:
        pass
    logout_user()
    return redirect(url_for('auth.login'))


# ──────────────────────────────────────────────
#  Google OAuth 2.0
# ──────────────────────────────────────────────

GOOGLE_AUTH_URL  = 'https://accounts.google.com/o/oauth2/v2/auth'
GOOGLE_TOKEN_URL = 'https://oauth2.googleapis.com/token'
GOOGLE_USER_URL  = 'https://www.googleapis.com/oauth2/v3/userinfo'
SCOPES = 'openid email profile'


@auth_bp.route('/google')
def google_login():
    if not current_app.config.get('GOOGLE_CLIENT_ID'):
        flash('Google OAuth не настроен', 'error')
        return redirect(url_for('auth.login'))

    state = secrets.token_urlsafe(16)
    session['oauth_state'] = state

    redirect_uri = url_for('auth.google_callback', _external=True)
    if not current_app.debug:
        redirect_uri = redirect_uri.replace('http://', 'https://')

    params = {
        'client_id':     current_app.config['GOOGLE_CLIENT_ID'],
        'redirect_uri':  redirect_uri,
        'response_type': 'code',
        'scope':         SCOPES,
        'state':         state,
        'access_type':   'online',
    }
    return redirect(f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}")


@auth_bp.route('/google/callback')
def google_callback():
    # Проверяем state
    if request.args.get('state') != session.pop('oauth_state', None):
        flash('Ошибка безопасности OAuth', 'error')
        return redirect(url_for('auth.login'))

    code = request.args.get('code')
    if not code:
        flash('Авторизация Google отменена', 'error')
        return redirect(url_for('auth.login'))

    # Обмен кода на токен
    callback_uri = url_for('auth.google_callback', _external=True)
    if not current_app.debug:
        callback_uri = callback_uri.replace('http://', 'https://')

    token_resp = requests.post(GOOGLE_TOKEN_URL, data={
        'code':          code,
        'client_id':     current_app.config['GOOGLE_CLIENT_ID'],
        'client_secret': current_app.config['GOOGLE_CLIENT_SECRET'],
        'redirect_uri':  callback_uri,
        'grant_type':    'authorization_code',
    })

    if not token_resp.ok:
        flash('Ошибка получения токена Google', 'error')
        return redirect(url_for('auth.login'))

    access_token = token_resp.json().get('access_token')

    # Получаем данные пользователя
    user_resp = requests.get(GOOGLE_USER_URL,
                             headers={'Authorization': f'Bearer {access_token}'})
    if not user_resp.ok:
        flash('Ошибка получения данных Google', 'error')
        return redirect(url_for('auth.login'))

    google_data = user_resp.json()
    google_id   = google_data.get('sub')
    email       = google_data.get('email', '').lower()
    name        = google_data.get('name', email)

    # Ищем пользователя
    user = User.query.filter_by(google_id=google_id).first()
    if not user:
        user = User.query.filter_by(email=email).first()

    if not user:
        flash('Ваш аккаунт не зарегистрирован. Обратитесь к администратору.', 'error')
        return redirect(url_for('auth.login'))

    if not user.is_active_user:
        flash('Ваш аккаунт деактивирован', 'error')
        return redirect(url_for('auth.login'))

    # Привязываем google_id если ещё не привязан
    if not user.google_id:
        user.google_id = google_id
        db.session.commit()

    login_user(user, remember=True)
    return redirect(url_for('index'))
