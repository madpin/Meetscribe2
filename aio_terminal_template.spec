# -*- mode: python ; coding: utf-8 -*-

"""
PyInstaller specification file for AIO Terminal Template.
This creates a single executable file that works across Linux, macOS, and Windows.
"""

import os
import sys

# Add the project root to the path for proper imports
current_dir = os.path.dirname(os.path.abspath(SPEC))
sys.path.insert(0, current_dir)

a = Analysis(
    ['app/cli.py'],
    pathex=[current_dir],
    binaries=[],
    datas=[
        ('config.toml', '.'),
    ],
    hiddenimports=[
        # Add any modules that might not be detected automatically
        'app.actions',
        'app.actions.registry',
        'app.actions.app',
        'app.actions.screenshot',
        'app.actions.network',
        'app.actions.clipboard',
        'app.core',
        'app.core.config',
        'app.core.context',
        'app.core.models',
        'app.core.logging',
        'app.core.exceptions',
        'app.core.utils',
        'app.shortcuts',
        'app.shortcuts.manager',
        'app.viewer',
        # Common hidden imports for CLI apps
        'rich',
        'typer',
        'toml',
        'requests',
        'PIL',
        'pyautogui',
        'pyperclip',
        'pynput',
        'daemon',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude unnecessary modules to reduce size and avoid dependency conflicts
        'tkinter',
        'unittest',
        'test',
        'pdb',
        'pydoc',
        'matplotlib',
        'numpy',
    ],
    noarchive=False,
    optimize=1,  # Enable basic optimizations
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='aio_terminal_template',
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
