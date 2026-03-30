# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for the SiEPIC Probe Stage *launcher*.

The resulting exe is a thin wrapper: it locates a Python interpreter
(venv / pyenv-win / system) and launches ``GUI/runner.py``.
No heavy dependencies are bundled — they stay in the Python environment.
"""

import os
from pathlib import Path

project_root = Path(SPECPATH).parent        # setup/ → project root

a = Analysis(
    [str(project_root / 'main.py')],
    pathex=[str(project_root)],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'numpy', 'scipy', 'pandas', 'matplotlib', 'plotly',
        'PIL', 'cv2', 'PyQt5', 'remi', 'tkinter',
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='SiEPIC_ProbeStage',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # Windowed — no black console flash
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,              # Replace with 'path/to/icon.ico' if available
)