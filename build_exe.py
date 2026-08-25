# build_exe.py
"""
Automated Build & Packaging Script for INDUS AI Desktop Assistant
Compiles INDUS into a standalone Windows Executable using PyInstaller.
"""

import os
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

def build():
    print("=" * 60)
    print("  INDUS — STANDALONE WINDOWS EXE COMPILER")
    print("=" * 60)

    # 1. Verify PyInstaller installation
    try:
        import PyInstaller
        print(f"[Build] PyInstaller version: {PyInstaller.__version__}")
    except ImportError:
        print("[Build] Installing PyInstaller...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)

    spec_path = BASE_DIR / "indus.spec"
    if not spec_path.exists():
        print(f"[Build] Error: spec file not found at {spec_path}")
        return False

    # 2. Run PyInstaller
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--clean",
        "-y",
        str(spec_path),
    ]

    print(f"[Build] Running command: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(BASE_DIR))

    if result.returncode == 0:
        dist_exe = BASE_DIR / "dist" / "INDUS" / "INDUS.exe"
        if not dist_exe.exists():
            dist_exe = BASE_DIR / "dist" / "INDUS.exe"
        print("=" * 60)
        print(f"[Build] [SUCCESS] Build Successful! Executable: {dist_exe}")
        print("=" * 60)
        return True
    else:
        print(f"[Build] [FAILED] Build failed with exit code: {result.returncode}")
        return False


if __name__ == "__main__":
    success = build()
    sys.exit(0 if success else 1)
