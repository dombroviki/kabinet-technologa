import os

# Определяем режим — десктоп (exe) или сервер (Render)
_IS_DESKTOP = not os.environ.get('RENDER')

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'my-super-secret-key-2026'

    if _IS_DESKTOP:
        SQLALCHEMY_DATABASE_URI = 'postgresql://neondb_owner:npg_tfQL4y5oeUub@ep-crimson-wave-alms31ub.c-3.eu-central-1.aws.neon.tech/neondb?sslmode=require'
    else:
        SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///tv_models.db'

    SQLALCHEMY_TRACK_MODIFICATIONS = False
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

    GOOGLE_CLIENT_ID     = os.environ.get('GOOGLE_CLIENT_ID', '')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')

    IMPORT_SECRET = os.environ.get('IMPORT_SECRET', 'QAR2nlYrAWHG2RMie94M5Qj-fP5M-7VaADwWX4E_HEE')

    SHEETS_CREDENTIALS_FILE = os.environ.get('SHEETS_CREDENTIALS_FILE') or \
        os.path.join(BASE_DIR, 'google_credentials.json')
    SHEETS_SPREADSHEET_ID = os.environ.get('SHEETS_SPREADSHEET_ID',
        '1rOj9tEkL_mFNV7d4Ao9hy0nlpAv495l6_ClCwqYqoNs')
