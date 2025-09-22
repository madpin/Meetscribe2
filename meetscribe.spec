# -*- mode: python ; coding: utf-8 -*-


block_cipher = None


a = Analysis(
    ['app/cli.py'],
    pathex=[],
    binaries=[],
    datas=[('config.toml', '.')],
    hiddenimports=[
        'ssl',
        '_ssl',
        'hashlib',
        '_hashlib',
        'cryptography',
        'OpenSSL',
        'httpx',
        'deepgram',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'psycopg2',
        'psycopg2-binary',
        # Heavy scientific libraries - exclude what's not needed
        'matplotlib',
        'scipy',
        'pandas', 
        'sklearn',
        'scikit-learn',
        'numba',
        'IPython',
        'jupyter',
        'notebook',
        'pytest',
        # GUI libraries
        'tkinter',
        'PyQt5',
        'PyQt6', 
        'PySide2',
        'PySide6',
        'wx',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='meetscribe',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
