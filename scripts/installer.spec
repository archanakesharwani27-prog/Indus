# -*- mode: python ; coding: utf-8 -*-
# installer.spec — Builds INDUS_Setup_2026.exe standalone graphical installer

import sys
from pathlib import Path

BASE_DIR = Path(SPECPATH).resolve().parent

added_files = [
    (str(BASE_DIR / "Indus_FInal_25_08_26.zip"), "."),
    (str(BASE_DIR / "face.png"), "."),
]

hidden_imports = [
    "PyQt6",
    "PyQt6.QtCore",
    "PyQt6.QtGui",
    "PyQt6.QtWidgets",
]

a = Analysis(
    ["installer.py"],
    pathex=[str(BASE_DIR / "scripts")],
    binaries=[],
    datas=added_files,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="INDUS_Setup_2026",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Pure GUI Window
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
