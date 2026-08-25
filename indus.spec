# -*- mode: python ; coding: utf-8 -*-
# indus.spec — PyInstaller build specification for INDUS AI Assistant

import sys
from pathlib import Path

block_cipher = None
# Automatically resolve BASE_DIR relative to this spec file — works on any machine
BASE_DIR = Path(SPECPATH).resolve()

added_files = [
    (str(BASE_DIR / "config"), "config"),
    (str(BASE_DIR / "memory"), "memory"),
    (str(BASE_DIR / "actions"), "actions"),
    (str(BASE_DIR / "core"), "core"),
    (str(BASE_DIR / "agent"), "agent"),
    (str(BASE_DIR / "scripts"), "scripts"),
    (str(BASE_DIR / "face.png"), "."),
]

hidden_imports = [
    "PyQt6",
    "PyQt6.QtCore",
    "PyQt6.QtGui",
    "PyQt6.QtWidgets",
    "google.genai",
    "sounddevice",
    "speech_recognition",
    "mss",
    "psutil",
    "PIL",
    "PIL.Image",
    "PIL.ImageGrab",
    "PIL.ImageDraw",
    "PIL.ImageChops",
    "pyautogui",
    "pycaw",
    "comtypes",
    "or_client",
    "cv2",
    "numpy",
    "requests",
    "bs4",
    "yt_dlp",
    "pytesseract",
    "groq",
    "openai",
    "actions.vision_engine",
    "actions.action_verifier",
    "actions.wake_word",
    "actions.computer_control",
    "actions.computer_settings",
    "actions.deep_research",
    "actions.mobile_bridge",
    "actions.live_writer",
    "actions.workspace_teleport",
    "actions.app_ui_navigator",
    "actions.video_editor",
    "actions.image_generator",
    "actions.smart_downloader",
    "actions.app_installer",
    "actions.universal_ad_skipper",
    "agent.agent_loop",
    "agent.planner",
    "agent.error_handler",
    "agent.task_model",
    "core.cancellation",
    "core.security_vault",
    "core.security_engine",
    "core.tool_registry",
    "core.tool_result",
    "core.vision_manager",
    "core.audit_logger",
    "core.confirmation_manager",
    "core.code_sandbox",
    "core.credential_redactor",
    "core.secure_storage",
    "core.event_bus",
    "memory.memory_manager",
    "memory.db_engine",
]

a = Analysis(
    ["main.py"],
    pathex=[str(BASE_DIR)],
    binaries=[],
    datas=added_files,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib"],
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
    name="Indus_FInal_25_08_26",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Live diagnostics & HUD console
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

