#!/usr/bin/env python3
"""
INDUS Preflight Dependency Check
=================================
Run this BEFORE starting INDUS to verify all required system dependencies
are installed and configured correctly.

Usage:
    python scripts/preflight_check.py
"""

import sys
import os
import shutil
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"

PASS = "  [PASS]"
FAIL = "  [FAIL]"
WARN = "  [WARN]"

results = []

def check(label, condition, message="", level="FAIL"):
    icon = PASS if condition else (WARN if level == "WARN" else FAIL)
    results.append((label, condition, level))
    if condition:
        print(f"{icon} {label}")
    else:
        print(f"{icon} {label}")
        if message:
            print(f"         FIX: {message}")

print("=" * 60)
print("  INDUS — Preflight Dependency Check")
print("=" * 60)

# ─── Python version ────────────────────────────────────────────
print("\n[Python]")
py_ok = sys.version_info >= (3, 10)
check("Python >= 3.10", py_ok, f"Install Python 3.10+. Found: {sys.version.split()[0]}")

# ─── API Keys ──────────────────────────────────────────────────
print("\n[API Keys]")
import json
config_exists = CONFIG_PATH.exists()
check("config/api_keys.json exists", config_exists,
      f"Create {CONFIG_PATH} with: {{\"gemini_api_key\": \"AIza...\"}}")

if config_exists:
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        check("gemini_api_key set", bool(data.get("gemini_api_key", "").strip()),
              "Add your Gemini API key to config/api_keys.json")
    except Exception as e:
        check("config/api_keys.json valid JSON", False, f"Fix JSON syntax: {e}")

# ─── Python packages ───────────────────────────────────────────
print("\n[Python Packages]")
REQUIRED = [
    ("google.genai", "google-genai"),
    ("PyQt6", "PyQt6"),
    ("sounddevice", "sounddevice"),
    ("PIL", "pillow"),
    ("pyautogui", "pyautogui"),
    ("mss", "mss"),
    ("psutil", "psutil"),
    ("requests", "requests"),
    ("bs4", "beautifulsoup4"),
    ("cv2", "opencv-python"),
    ("numpy", "numpy"),
    ("pyperclip", "pyperclip"),
    ("yt_dlp", "yt-dlp"),
    ("pytesseract", "pytesseract"),
]

for module, pkg in REQUIRED:
    try:
        __import__(module)
        check(pkg, True)
    except ImportError:
        check(pkg, False, f"pip install {pkg}")

# ─── Optional packages (WARN not FAIL) ────────────────────────
print("\n[Optional Packages]")
OPTIONAL = [
    ("moviepy", "moviepy", "Required for video_editor tool"),
    ("playwright", "playwright", "Required for browser_control tool (also: playwright install)"),
    ("pycaw", "pycaw", "Required for volume control on Windows"),
    ("comtypes", "comtypes", "Required for Windows COM automation"),
]

for module, pkg, reason in OPTIONAL:
    try:
        __import__(module)
        check(f"{pkg}", True)
    except ImportError:
        print(f"{WARN} {pkg} not installed ({reason})")
        print(f"         FIX: pip install {pkg}")

# ─── System binaries ───────────────────────────────────────────
print("\n[System Binaries]")
tesseract = shutil.which("tesseract") or Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe").exists()
check("Tesseract-OCR binary", bool(tesseract),
      "Download from: https://github.com/UB-Mannheim/tesseract/wiki")

ffmpeg = bool(shutil.which("ffmpeg"))
print(f"{'  [PASS]' if ffmpeg else '  [WARN]'} FFmpeg {'found' if ffmpeg else 'not found (needed for video_editor)'}")
if not ffmpeg:
    print("         FIX: Download from https://ffmpeg.org/download.html and add to PATH")

# ─── Audio device ──────────────────────────────────────────────
print("\n[Audio]")
try:
    import sounddevice as sd
    devs = sd.query_devices()
    inputs  = [d for d in devs if d["max_input_channels"] > 0]
    outputs = [d for d in devs if d["max_output_channels"] > 0]
    check("Input device (microphone) found", len(inputs) > 0,
          "Connect a microphone")
    check("Output device (speakers) found", len(outputs) > 0,
          "Connect speakers or headphones")
except Exception as e:
    check("Audio system (sounddevice)", False, f"Check sounddevice/PortAudio install: {e}")

# ─── Summary ───────────────────────────────────────────────────
print("\n" + "=" * 60)
failures = [r for r in results if not r[1] and r[2] == "FAIL"]
warnings = [r for r in results if not r[1] and r[2] == "WARN"]

if not failures:
    print("  RESULT: ALL CHECKS PASSED — INDUS is ready to start!")
    print("  Run: python main.py")
else:
    print(f"  RESULT: {len(failures)} check(s) FAILED — fix above issues first")
print("=" * 60)
sys.exit(0 if not failures else 1)
