# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Десктоп — окно над сервером (см. SERVER_URL в desktop.py): ни шаблонов, ни Flask,
# ни секретов в сборке не нужно.
a = Analysis(
    ['desktop.py'],
    pathex=['.'],
    binaries=[],
    datas=[],
    hiddenimports=[
        'webview',
        'webview.platforms.winforms',
        'webview.platforms.edgechromium',
        'clr',
        'requests',
        'pystray',
        'pystray._win32',
        'PIL.Image',
        'PIL.ImageDraw',
        'tkinter',
        'tkinter.font',
        'tkinter.messagebox',
        '_tkinter',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Страховка: серверный код и секреты не должны попасть в exe, даже если
    # кто-то случайно их импортирует
    excludes=['app', 'config', 'secrets_local', 'creds', 'flask', 'sqlalchemy', 'psycopg2'],
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
