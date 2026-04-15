"""
Хранение зашифрованных учётных данных для десктоп-приложения.
Ключ шифрования привязан к машине (hostname + username).
"""
import os
import hashlib
import base64
import json

CREDS_DIR = os.path.join(os.path.expanduser('~'), '.kabinet_technologa')
CREDS_FILE = os.path.join(CREDS_DIR, 'creds')


def _get_key():
    """Генерирует ключ Fernet из машинного fingerprint."""
    from cryptography.fernet import Fernet
    import platform
    fingerprint = f"{platform.node()}:{os.environ.get('USERNAME') or os.environ.get('USER') or 'user'}"
    raw = hashlib.sha256(fingerprint.encode()).digest()
    return base64.urlsafe_b64encode(raw)


def save_credentials(email: str, password: str):
    try:
        from cryptography.fernet import Fernet
        os.makedirs(CREDS_DIR, exist_ok=True)
        f = Fernet(_get_key())
        data = json.dumps({'email': email, 'password': password}).encode()
        with open(CREDS_FILE, 'wb') as fp:
            fp.write(f.encrypt(data))
    except Exception:
        pass


def load_credentials():
    """Возвращает (email, password) или None."""
    try:
        from cryptography.fernet import Fernet
        if not os.path.exists(CREDS_FILE):
            return None
        f = Fernet(_get_key())
        with open(CREDS_FILE, 'rb') as fp:
            data = f.decrypt(fp.read())
        creds = json.loads(data.decode())
        return creds['email'], creds['password']
    except Exception:
        return None


def clear_credentials():
    try:
        if os.path.exists(CREDS_FILE):
            os.remove(CREDS_FILE)
    except Exception:
        pass
