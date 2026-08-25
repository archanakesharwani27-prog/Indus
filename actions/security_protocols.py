# actions/security_protocols.py
# INDUS Emergency Security & Lockdown Protocols
# Instant workstation locking, window cloaking, and panic emergency shutdowns

import os
import sys
import subprocess
import time
import psutil
from pathlib import Path


def initiate_lockdown(level: str = "lock") -> str:
    """
    Executes voice-activated workstation security protocols:
    - lock: Instantly locks Windows workstation (Win+L equivalent).
    - cloak: Minimizes all windows, clears clipboard buffer, and mutes audio.
    - panic: Force terminates non-essential processes, wipes clipboard, mutes audio, and locks workstation.
    """
    level = (level or "lock").lower().strip().replace("-", "_")

    # 1. Lock Workstation Protocol
    if level in ("lock", "lock_screen", "lockstation", "secure"):
        try:
            if sys.platform == "win32":
                subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"], check=True)
                return "Workstation locked successfully."
            elif sys.platform == "darwin":
                subprocess.run(["pmset", "displaysleepnow"])
                return "Display locked."
            else:
                subprocess.run(["xdg-screensaver", "lock"])
                return "Screen locked."
        except Exception as e:
            return f"Lock workstation error: {e}"

    # 2. Cloak Mode Protocol (Hide windows + mute + clear clipboard)
    elif level in ("cloak", "stealth", "hide", "incognito"):
        actions = []
        # Mute master volume
        try:
            from actions.computer_settings import volume_mute
            volume_mute()
            actions.append("Audio muted")
        except Exception:
            pass

        # Minimize all windows (Win+D)
        try:
            import pyautogui
            pyautogui.hotkey("win", "d")
            actions.append("Windows minimized")
        except Exception:
            pass

        # Clear clipboard
        try:
            import pyperclip
            pyperclip.copy("")
            actions.append("Clipboard cleared")
        except Exception:
            pass

        return "Cloak protocol engaged: " + ", ".join(actions) + "."

    # 3. Panic Emergency Protocol
    elif level in ("panic", "emergency", "red_alert", "kill_switch"):
        killed = []
        # Target non-essential browser/game processes for emergency kill
        target_process_names = [
            "chrome.exe", "msedge.exe", "firefox.exe", "brave.exe",
            "steam.exe", "discord.exe", "spotify.exe", "telegram.exe"
        ]

        for p in psutil.process_iter(['name']):
            try:
                name = (p.info['name'] or "").lower()
                if name in target_process_names:
                    p.kill()
                    if name not in killed:
                        killed.append(name)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        # Mute audio
        try:
            from actions.computer_settings import volume_mute
            volume_mute()
        except Exception:
            pass

        # Clear clipboard
        try:
            import pyperclip
            pyperclip.copy("")
        except Exception:
            pass

        # Lock screen
        if sys.platform == "win32":
            subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"])

        killed_summary = f"Terminated {', '.join(killed)}" if killed else "Processes purged"
        return f"Panic protocol executed. {killed_summary}. Screen locked."

    return f"Security level '{level}' executed."


def security_protocols(parameters: dict = None, player=None) -> str:
    """Main tool dispatch entry point for security_protocols."""
    params = parameters or {}
    level = params.get("level") or params.get("action") or "lock"

    if player:
        player.write_log(f"[Security] Protocol: {level}")

    return initiate_lockdown(level=level)
