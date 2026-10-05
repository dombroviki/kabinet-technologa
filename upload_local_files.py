"""
Разовый перенос локальных загрузок в бакет (S3_* из .env / secrets_local).

Запуск: python upload_local_files.py [папка_uploads]
По умолчанию — app/static/uploads проекта (там лежали загрузки до переноса
папки из static). Для файлов из старого exe (≤1.8):
  python upload_local_files.py "%LOCALAPPDATA%\\Programs\\Кабинет технолога\\_internal\\app\\static\\uploads"

Кладёт photos/* и firmware/* под теми же именами, что записаны в БД.
Уже существующие в бакете файлы пропускает. БД не трогает.
"""
import os
import sys
import mimetypes
from dotenv import load_dotenv
load_dotenv()

from config import Config

src = sys.argv[1] if len(sys.argv) > 1 else Config.LEGACY_UPLOAD_FOLDER
if not Config.S3_BUCKET:
    sys.exit('S3_BUCKET не задан — сначала настрой бакет (.env или secrets_local.py)')

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError

s3 = boto3.client(
    's3',
    endpoint_url=Config.S3_ENDPOINT_URL or None,
    aws_access_key_id=Config.S3_ACCESS_KEY,
    aws_secret_access_key=Config.S3_SECRET_KEY,
    region_name=Config.S3_REGION or 'auto',
    config=BotoConfig(signature_version='s3v4'),
)

uploaded = skipped = 0
for folder in ('photos', 'firmware'):
    d = os.path.join(src, folder)
    if not os.path.isdir(d):
        continue
    for name in sorted(os.listdir(d)):
        path = os.path.join(d, name)
        if not os.path.isfile(path):
            continue
        key = f'{folder}/{name}'
        try:
            s3.head_object(Bucket=Config.S3_BUCKET, Key=key)
            skipped += 1
            continue
        except ClientError:
            pass
        ctype = mimetypes.guess_type(name)[0] or 'application/octet-stream'
        s3.upload_file(path, Config.S3_BUCKET, key, ExtraArgs={'ContentType': ctype})
        print(f'✅ {key}')
        uploaded += 1

print(f'Готово: загружено {uploaded}, уже были {skipped}. Источник: {src}')
