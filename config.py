import os

# Секреты: env (Render dashboard + локальный .env) → secrets_local (для локальной
# разработки) → дефолт. secrets_local.py в .gitignore; в exe он больше не попадает —
# десктоп работает через сервер и секретов не содержит.
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


_ON_RENDER = bool(os.environ.get('RENDER'))

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
    REMEMBER_COOKIE_HTTPONLY = True
    # На Render всё по https — куки входа не уходят по http. Локально (http) — можно.
    REMEMBER_COOKIE_SECURE = _ON_RENDER
    SESSION_COOKIE_SECURE = _ON_RENDER

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    # Локальная папка загрузок — только если бакет не задан (см. app/storage.py).
    # Вне app/static: иначе Flask раздавал бы файлы по /static/uploads/ без логина.
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    # Где лежали загрузки до переноса (для upload_local_files.py)
    LEGACY_UPLOAD_FOLDER = os.path.join(BASE_DIR, 'app', 'static', 'uploads')

    # S3-совместимый бакет для фото и прошивок (Cloudflare R2 / Backblaze B2 / AWS S3).
    # Для R2: S3_ENDPOINT_URL=https://<account_id>.r2.cloudflarestorage.com, S3_REGION=auto
    S3_BUCKET       = _secret('S3_BUCKET', '')
    S3_ENDPOINT_URL = _secret('S3_ENDPOINT_URL', '')
    S3_ACCESS_KEY   = _secret('S3_ACCESS_KEY', '')
    S3_SECRET_KEY   = _secret('S3_SECRET_KEY', '')
    S3_REGION       = _secret('S3_REGION', 'auto')
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
