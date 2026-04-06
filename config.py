import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'change-this-in-production-please'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///tv_models.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'app', 'static', 'uploads')
    MAX_CONTENT_LENGTH = MAX_CONTENT_LENGTH = 2 * 1024 * 1024 * 1024  # 
    ALLOWED_EXTENSIONS_PHOTO = {'png', 'jpg', 'jpeg', 'gif'}
    ALLOWED_EXTENSIONS_FIRMWARE = {'bin', 'zip', 'img', 'hex'}

    # Google OAuth — заполни своими значениями из Google Console
    # Если оставить пустыми — кнопка Google не появится
    GOOGLE_CLIENT_ID     = os.environ.get('GOOGLE_CLIENT_ID', '')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')
