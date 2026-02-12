# -*- mode: python ; coding: utf-8 -*-

import os
from pathlib import Path

# Get the project root directory
project_root = Path(SPECPATH)

# Define data files and directories to include
datas = [
    # GUI resources
    ('GUI/res', 'GUI/res'),
    ('GUI/database', 'GUI/database'),
    
    # Hardware driver files (if any DLLs or data files exist)
    # ('NIR/drivers/data', 'NIR/drivers/data'),  # uncomment if needed
    
    # Configuration files
    ('requirements.txt', '.'),
]

# Hidden imports - modules that PyInstaller might miss
hiddenimports = [
    # GUI modules
    'GUI.lib_gui',
    'GUI.lib_coordinates', 
    'GUI.lib_tsp',
    
    # Hardware modules
    'motors.stage_manager',
    'motors.config.stage_config',
    'motors.hal.motors_hal',
    'motors.utils.shared_memory',
    
    'NIR.nir_manager',
    'NIR.config.nir_config',
    'NIR.drivers',
    
    'LDC.ldc_manager',
    'LDC.config.ldc_config',
    
    'measure.area_sweep',
    'measure.fine_align',
    'measure.config.area_sweep_config',
    'measure.config.fine_align_config',
    
    # External libraries that might need explicit inclusion
    'remi',
    'pyserial',
    'pyserial_asyncio',
    'pyvisa',
    'comtypes',
    'pythonnet',
    'plotly',
    'matplotlib',
    'numpy',
    'scipy',
    'pandas',
    'ortools',
    'webview',
    'PyQt5',
    'tkinter',
]

# Binaries - include any DLL files or compiled extensions
binaries = []

# Exclude unnecessary modules to reduce size
excludes = [
    'test',
    'tests',
    'unittest',
    'pdb',
    'doctest',
    'difflib',
]

a = Analysis(
    ['main.py'],
    pathex=[str(project_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
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
    name='ProbeStage',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Set to False for windowed app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon path if you have one: 'path/to/icon.ico'
)