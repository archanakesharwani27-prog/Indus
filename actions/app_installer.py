# actions/app_installer.py
"""
INDUS Autonomous Software & App Installer Engine
=================================================
Automates installing, updating, and removing Windows applications & developer packages.

Capabilities:
1. Winget (Windows Package Manager) silent installation:
   Chrome, VS Code, Discord, Spotify, Steam, VLC, Blender, Telegram, 7-Zip, Git, Node, Python, etc.
2. Direct Installer (.exe / .msi) silent execution & smart download.
3. Python packages (pip) & Node packages (npm).
4. App uninstallation & update checks.
"""

from __future__ import annotations
import glob
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("IndusAppInstaller")

# Well-known Winget Application IDs
KNOWN_WINGET_IDS = {
    "chrome": "Google.Chrome",
    "google chrome": "Google.Chrome",
    "brave": "Brave.Brave",
    "firefox": "Mozilla.Firefox",
    "edge": "Microsoft.Edge",
    "vscode": "Microsoft.VisualStudioCode",
    "vs code": "Microsoft.VisualStudioCode",
    "visual studio code": "Microsoft.VisualStudioCode",
    "spotify": "Spotify.Spotify",
    "discord": "Discord.Discord",
    "telegram": "Telegram.TelegramDesktop",
    "whatsapp": "WhatsApp.WhatsApp",
    "vlc": "VideoLAN.VLC",
    "steam": "Valve.Steam",
    "git": "Git.Git",
    "nodejs": "OpenJS.NodeJS",
    "node": "OpenJS.NodeJS",
    "python": "Python.Python.3.12",
    "7zip": "7zip.7zip",
    "7-zip": "7zip.7zip",
    "winrar": "RARLab.WinRAR",
    "notepad++": "Notepad++.Notepad++",
    "notepadplusplus": "Notepad++.Notepad++",
    "obs": "OBSProject.OBSStudio",
    "obs studio": "OBSProject.OBSStudio",
    "blender": "BlenderFoundation.Blender",
    "unity": "Unity.UnityHub",
    "epic games": "EpicGames.EpicGamesLauncher",
    "postman": "Postman.Postman",
    "docker": "Docker.DockerDesktop",
    "github desktop": "GitHub.GitHubDesktop",
    "audacity": "Audacity.Audacity",
    "gimp": "GIMP.GIMP",
    "zoom": "Zoom.Zoom",
    "slack": "SlackTechnologies.Slack",
    "anydesk": "AnyDeskSoftwareGmbH.AnyDesk",
    "teamviewer": "TeamViewer.TeamViewer",
    "qbittorrent": "qBittorrent.qBittorrent",
    "vlc media player": "VideoLAN.VLC",
    "sublime": "SublimeHQ.SublimeText.4",
    "sublime text": "SublimeHQ.SublimeText.4",
    "rust": "Rustlang.Rustup",
    "golang": "GoLang.Go",
    "go": "GoLang.Go",
}


def _find_winget_exe() -> Optional[str]:
    """Finds winget executable on Windows 11."""
    # 1. System PATH
    w = shutil.which("winget")
    if w and os.path.exists(w):
        return w

    # 2. WindowsApps user local directory
    user_app = Path.home() / "AppData" / "Local" / "Microsoft" / "WindowsApps" / "winget.exe"
    if user_app.exists():
        return str(user_app)

    # 3. Program Files WindowsApps
    matches = glob.glob(r"C:\Program Files\WindowsApps\Microsoft.DesktopAppInstaller_*\winget.exe")
    if matches:
        return matches[0]

    return None


def install_app(
    app_name: str,
    source: str = "auto",
    silent: bool = True,
    player=None
) -> str:
    """
    Installs an application using Winget, pip, npm, or direct installer.
    """
    clean_app = app_name.lower().strip()
    if not clean_app:
        return "Please specify the app or software name to install."

    if player:
        player.write_log(f"[Installer] Installing '{app_name}'...")

    # 1. Check Python package (pip)
    if source == "pip" or clean_app.startswith("pip "):
        pkg = clean_app.replace("pip install", "").replace("pip ", "").strip()
        cmd = [sys.executable, "-m", "pip", "install", pkg]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if res.returncode == 0:
            return f"Python package '{pkg}' successfully install ho gaya!"
        return f"Pip install failed: {res.stderr[:200]}"

    # 2. Check Node package (npm)
    if source == "npm" or clean_app.startswith("npm "):
        pkg = clean_app.replace("npm install -g", "").replace("npm install", "").replace("npm ", "").strip()
        cmd = ["npm", "install", "-g", pkg]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=120, shell=True)
            if res.returncode == 0:
                return f"NPM package '{pkg}' successfully install ho gaya!"
            return f"NPM install error: {res.stderr[:200]}"
        except Exception as e:
            return f"NPM execution error: {e}"

    # 3. Check Winget (Windows Package Manager)
    winget = _find_winget_exe()
    if winget:
        app_id = KNOWN_WINGET_IDS.get(clean_app)

        if app_id:
            cmd = [
                winget, "install", "--id", app_id,
                "--exact", "--accept-package-agreements", "--accept-source-agreements"
            ]
            if silent:
                cmd.append("--silent")
        else:
            cmd = [
                winget, "install", app_name,
                "--accept-package-agreements", "--accept-source-agreements"
            ]
            if silent:
                cmd.append("--silent")

        try:
            if player:
                player.write_log(f"[Installer] Running Winget for {app_name}...")
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            stdout = res.stdout
            if res.returncode == 0 or "Successfully installed" in stdout or "succeeded" in stdout.lower():
                return f"'{app_name}' successfully install ho gaya!"
            elif "No package found" in stdout or "No applicable update found" in stdout:
                logger.warning(f"[Installer] Winget package not found for {app_name}, trying fallback...")
            else:
                if "Successfully installed" in stdout:
                    return f"'{app_name}' successfully install ho gaya!"
        except Exception as e:
            logger.error(f"[Installer] Winget exception: {e}")

    # 4. Fallback: Smart Downloader + Direct Installer
    if player:
        player.write_log(f"[Installer] Searching official installer for {app_name}...")

    from actions.smart_downloader import smart_downloader
    dl_res = smart_downloader({"item_name": f"{app_name} installer", "action": "download"}, player=player)

    # Check if a downloaded installer (.exe / .msi) was saved in Downloads
    dl_dir = Path.home() / "Downloads" / "IndusDownloads"
    recent_installers = list(dl_dir.glob("*.exe")) + list(dl_dir.glob("*.msi"))
    if recent_installers:
        recent_installers.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        newest = recent_installers[0]
        if (time.time() - newest.stat().st_mtime) < 120:
            # Run installer
            try:
                if newest.suffix.lower() == ".msi":
                    subprocess.Popen(["msiexec.exe", "/i", str(newest), "/qn"])
                else:
                    subprocess.Popen([str(newest), "/S"])
                return f"'{app_name}' ka installer download karke background mein install start kar diya hai!"
            except Exception as e:
                os.startfile(str(newest))
                return f"'{app_name}' ka installer open ho gaya hai, screen par setup complete karein."

    return f"'{app_name}' installation request process ho gayi. {dl_res}"


def uninstall_app(app_name: str, silent: bool = True, player=None) -> str:
    """Uninstalls an application via Winget."""
    clean_app = app_name.lower().strip()
    if not clean_app:
        return "Please specify the app name to uninstall."

    winget = _find_winget_exe()
    if not winget:
        return "Winget package manager not found."

    app_id = KNOWN_WINGET_IDS.get(clean_app)
    if app_id:
        cmd = [winget, "uninstall", "--id", app_id, "--exact"]
    else:
        cmd = [winget, "uninstall", app_name]

    if silent:
        cmd.append("--silent")

    if player:
        player.write_log(f"[Installer] Uninstalling '{app_name}'...")

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if res.returncode == 0 or "Successfully uninstalled" in res.stdout:
            return f"'{app_name}' successfully uninstall ho gaya!"
        return f"Uninstall completed with status: {res.stdout.strip() or res.stderr.strip()}"
    except Exception as e:
        return f"Uninstall failed: {e}"


def app_installer(parameters: dict = None, player=None, speak=None) -> str:
    """
    Main tool handler for app_installer.
    Parameters:
    - action: 'install' | 'uninstall' | 'search' | 'update'
    - app_name: Name of the application/software
    - source: 'auto' | 'winget' | 'pip' | 'npm'
    """
    params = parameters or {}
    action = params.get("action", "install").lower().strip()
    app_name = params.get("app_name") or params.get("name") or params.get("software") or ""
    source = params.get("source", "auto").lower().strip()

    if action in ("uninstall", "remove", "delete_app"):
        return uninstall_app(app_name=app_name, player=player)

    elif action in ("install", "setup", "get", "add"):
        return install_app(app_name=app_name, source=source, player=player)

    elif action in ("search", "find"):
        winget = _find_winget_exe()
        if winget:
            r = subprocess.run([winget, "search", app_name], capture_output=True, text=True, timeout=15)
            return r.stdout[:600] or "No app found."
        return "Winget not available to search."

    return install_app(app_name=app_name, source=source, player=player)
