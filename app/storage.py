"""Хранилище загрузок (фото, прошивки).

Заданы S3_* — файлы живут в S3-совместимом бакете (Cloudflare R2, Backblaze B2,
AWS S3). Не заданы — в UPLOAD_FOLDER на диске, как раньше (локальная разработка).
На Render диск эфемерный: без бакета загрузки пропадают при деплое/рестарте.

Ключ в бакете = '<folder>/<filename>', filename — тот же, что хранится в БД.
"""
import os
from urllib.parse import quote
from flask import current_app, redirect, send_from_directory

# Ссылка на файл в бакете живёт столько секунд — хватает начать скачивание
_URL_TTL = 600


def _bucket():
    return current_app.config.get('S3_BUCKET') or None


def _client():
    client = current_app.extensions.get('s3_client')
    if client is None:
        import boto3
        from botocore.config import Config as BotoConfig
        cfg = current_app.config
        client = boto3.client(
            's3',
            endpoint_url=cfg.get('S3_ENDPOINT_URL') or None,
            aws_access_key_id=cfg.get('S3_ACCESS_KEY'),
            aws_secret_access_key=cfg.get('S3_SECRET_KEY'),
            region_name=cfg.get('S3_REGION') or 'auto',
            config=BotoConfig(signature_version='s3v4'),
        )
        current_app.extensions['s3_client'] = client
    return client


def _local_dir(folder):
    return os.path.join(current_app.config['UPLOAD_FOLDER'], folder)


def save(file, folder, filename):
    """Сохраняет werkzeug FileStorage под именем filename."""
    bucket = _bucket()
    if bucket:
        _client().upload_fileobj(
            file.stream, bucket, f'{folder}/{filename}',
            ExtraArgs={'ContentType': file.mimetype or 'application/octet-stream'})
        return
    os.makedirs(_local_dir(folder), exist_ok=True)
    file.save(os.path.join(_local_dir(folder), filename))


def delete(folder, filename):
    if not filename:
        return
    bucket = _bucket()
    if bucket:
        try:
            _client().delete_object(Bucket=bucket, Key=f'{folder}/{filename}')
        except Exception as e:
            # Запись в БД всё равно удаляем — осиротевший файл в бакете не страшен
            current_app.logger.warning(f'storage.delete {folder}/{filename}: {e}')
        return
    path = os.path.join(_local_dir(folder), filename)
    if os.path.exists(path):
        os.remove(path)


def send(folder, filename, download_name=None, as_attachment=False):
    """Ответ с файлом: из бакета — редирект на временную подписанную ссылку,
    локально — сам файл."""
    bucket = _bucket()
    if bucket:
        params = {'Bucket': bucket, 'Key': f'{folder}/{filename}'}
        if as_attachment:
            name = quote(download_name or filename)
            params['ResponseContentDisposition'] = f"attachment; filename*=UTF-8''{name}"
        url = _client().generate_presigned_url('get_object', Params=params, ExpiresIn=_URL_TTL)
        resp = redirect(url)
        # Браузер может переиспользовать редирект, пока ссылка точно жива
        resp.headers['Cache-Control'] = f'private, max-age={_URL_TTL // 2}'
        return resp
    return send_from_directory(_local_dir(folder), filename,
                               as_attachment=as_attachment, download_name=download_name)
