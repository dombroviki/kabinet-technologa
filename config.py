import os

# Секреты: env (Render dashboard + локальный .env) → secrets_local (бандлится в exe)
# → дефолт. secrets_local.py в .gitignore и в публичный репо не попадает.
try:
    import secrets_local as _local
except ImportError:
    _local = None


def _secret(name, default=None):
    val = os.environ.get(name)
    if val:
        return val
    if _local is not None:
        val = getattr(_local, name, None)
        if val:
            return val
    return default


# Определяем режим — десктоп (exe) или сервер (Render)
_IS_DESKTOP = not os.environ.get('RENDER')

class Config:
    # Если ключ нигде не задан — генерим временный (сессии слетят при рестарте)
    SECRET_KEY = _secret('SECRET_KEY')
    if not SECRET_KEY:
        import secrets as _secrets_mod
        SECRET_KEY = _secrets_mod.token_hex(32)
        print('[WARN] SECRET_KEY не задан — использую временный. Задай env SECRET_KEY на проде!')

    SQLALCHEMY_DATABASE_URI = _secret('DATABASE_URL', 'sqlite:///tv_models.db')

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_size': 5,
        'max_overflow': 2,
    }

    REMEMBER_COOKIE_DURATION = 60 * 60 * 24 * 30  # 30 дней
    REMEMBER_COOKIE_SECURE = False
    REMEMBER_COOKIE_HTTPONLY = True

    # Серверные сессии для десктопа (куки webview не сохраняются)
    if _IS_DESKTOP:
        SESSION_TYPE = 'filesystem'
        SESSION_FILE_DIR = os.path.join(os.path.expanduser('~'), '.kabinet_technologa', 'sessions')
        SESSION_PERMANENT = True
        PERMANENT_SESSION_LIFETIME = 60 * 60 * 24 * 30  # 30 дней
        SESSION_FILE_THRESHOLD = 100
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'app', 'static', 'uploads')
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024 * 1024

    ALLOWED_EXTENSIONS_PHOTO = {'png', 'jpg', 'jpeg', 'gif'}
    ALLOWED_EXTENSIONS_FIRMWARE = {'bin', 'zip', 'img', 'hex'}

    GOOGLE_CLIENT_ID     = _secret('GOOGLE_CLIENT_ID', '')
    GOOGLE_CLIENT_SECRET = _secret('GOOGLE_CLIENT_SECRET', '')

    # Пусто по умолчанию — авто-импорт отключён, пока секрет не задан (fail-safe,
    # вместо известного на весь интернет токена)
    IMPORT_SECRET = _secret('IMPORT_SECRET', '')

    SHEETS_CREDENTIALS_FILE = os.environ.get('SHEETS_CREDENTIALS_FILE') or \
        os.path.join(BASE_DIR, 'google_credentials.json')
    # ID таблицы — не секрет, оставляем
    SHEETS_SPREADSHEET_ID = _secret('SHEETS_SPREADSHEET_ID',
        '1rOj9tEkL_mFNV7d4Ao9hy0nlpAv495l6_ClCwqYqoNs')
