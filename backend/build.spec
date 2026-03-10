# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.building.build_main import Analysis, PYZ, EXE, COLLECT
import sys
import os
from pathlib import Path

block_cipher = None

# Add virtual environment to path if running from venv
venv_path = Path(sys.executable).parent.parent / 'Lib' / 'site-packages'
if venv_path.exists():
    sys.path.insert(0, str(venv_path))

# When running from backend directory, paths are relative
# The spec file is in backend/, and frontend is in ../frontend
a = Analysis(
    ['build_entry.py'],
    pathex=[os.getcwd(), str(venv_path)],
    binaries=[],
    datas=[
        ('app', 'app'),
        (r'..\frontend\dist', r'frontend\dist'),
        ('data/vanilla', 'data/vanilla'),
    ],
    hiddenimports=[
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'win32api',
        'win32con',
        'win32process',
        'win32security',
        'win32event',
        'win32gui',
        'winerror',
        'pydantic',
        'pydantic.v1',
        'pydantic_settings',
        'pydantic.deprecated',
        'pydantic.deprecated.decorator',
        'pydantic_core',
        'fastapi',
        'fastapi.routing',
        'fastapi.middleware',
        'fastapi.middleware.cors',
        'fastapi.staticfiles',
        'fastapi.responses',
        'starlette',
        'starlette.routing',
        'starlette.middleware',
        'starlette.middleware.cors',
        'starlette.staticfiles',
        'starlette.responses',
        'toml',
        'anyio',
        'anyio._backends',
        'anyio._backends._asyncio',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy',
        'pandas',
        'PIL',
        'scipy',
        'PyQt5',
        'PyQt6',
        'PySide2',
        'PySide6',
        'tkinter',
        'unittest',
        'test',
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
    name='QuantumSelector',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Set to False for windowed mode, True for console output
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
