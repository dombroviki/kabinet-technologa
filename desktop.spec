# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Собираем все данные приложения
added_files = [
    ('app/templates', 'app/templates'),
    ('app/static', 'app/static'),
    ('config.py', '.'),
    ('version.py', '.'),
]

a = Analysis(
    ['desktop.py'],
    pathex=['.'],
    binaries=[],
    datas=added_files,
    hiddenimports=[
        'webview',
        'webview.platforms.winforms',
        'clr',
        'flask',
        'flask_login',
        'flask_sqlalchemy',
        'flask_wtf',
        'sqlalchemy',
        'psycopg2',
        'openpyxl',
        'gspread',
        'google.oauth2',
        'google.auth',
        'requests',
        'email_validator',
        'tkinter',
        'tkinter.font',
        '_tkinter',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='КабинетТехнолога',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # без консольного окна
    icon='icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='КабинетТехнолога',
)
