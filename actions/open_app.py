# actions/open_app.py
# INDUS Jarvis App Launcher — Cross-Platform App Launcher with Web & Antigravity Support

import time
import subprocess
import platform
import shutil
import os
import re
import webbrowser
from pathlib import Path

try:
    import psutil
    _PSUTIL = True
except ImportError:
    _PSUTIL = False

_APP_ALIASES = {
    "whatsapp":           {"Windows": "WhatsApp",               "Darwin": "WhatsApp",            "Linux": "whatsapp"},
    "chrome":             {"Windows": "chrome",                 "Darwin": "Google Chrome",       "Linux": "google-chrome"},
    "google chrome":      {"Windows": "chrome",                 "Darwin": "Google Chrome",       "Linux": "google-chrome"},
    "firefox":            {"Windows": "firefox",                "Darwin": "Firefox",             "Linux": "firefox"},
    "spotify":            {"Windows": "Spotify",                "Darwin": "Spotify",             "Linux": "spotify"},
    "vscode":             {"Windows": "code",                  "Darwin": "Visual Studio Code",  "Linux": "code"},
    "vs code":            {"Windows": "code",                  "Darwin": "Visual Studio Code",  "Linux": "code"},
    "visual studio code": {"Windows": "code",                  "Darwin": "Visual Studio Code",  "Linux": "code"},
    "antigravity":        {"Windows": "antigravity",          "Darwin": "Antigravity",       "Linux": "antigravity"},
    "youtube":            {"Windows": "https://www.youtube.com", "Darwin": "https://www.youtube.com", "Linux": "https://www.youtube.com"},
    "discord":            {"Windows": "Discord",                "Darwin": "Discord",             "Linux": "discord"},
    "telegram":           {"Windows": "Telegram",               "Darwin": "Telegram",            "Linux": "telegram"},
    "instagram":          {"Windows": "Instagram",              "Darwin": "Instagram",           "Linux": "instagram"},
    "tiktok":             {"Windows": "TikTok",                "Darwin": "TikTok",             "Linux": "tiktok"},
    "notepad":            {"Windows": "notepad.exe",          "Darwin": "TextEdit",           "Linux": "gedit"},
    "calculator":         {"Windows": "calc.exe",             "Darwin": "Calculator",        "Linux": "gnome-calculator"},
    "terminal":           {"Windows": "cmd.exe",              "Darwin": "Terminal",          "Linux": "gnome-terminal"},
    "cmd":                {"Windows": "cmd.exe",              "Darwin": "Terminal",          "Linux": "bash"},
    "explorer":           {"Windows": "explorer.exe",         "Darwin": "Finder",            "Linux": "nautilus"},
    "file explorer":     {"Windows": "explorer.exe",         "Darwin": "Finder",            "Linux": "nautilus"},
    "paint":              {"Windows": "mspaint.exe",         "Darwin": "Preview",           "Linux": "gimp"},
    "word":               {"Windows": "winword",              "Darwin": "Microsoft Word",      "Linux": "libreoffice --writer"},
    "excel":              {"Windows": "excel",               "Darwin": "Microsoft Excel",     "Linux": "libreoffice --calc"},
    "powerpoint":         {"Windows": "powerpnt",             "Darwin": "Microsoft PowerPoint","Linux": "libreoffice --impress"},
    "vlc":                {"Windows": "vlc",                  "Darwin": "VLC",               "Linux": "vlc"},
    "zoom":               {"Windows": "Zoom",                 "Darwin": "zoom.us",           "Linux": "zoom"},
    "slack":              {"Windows": "Slack",                "Darwin": "Slack",             "Linux": "slack"},
    "steam":              {"Windows": "steam",                "Darwin": "Steam",             "Linux": "steam"},
    "task manager":       {"Windows": "taskmgr.exe",         "Darwin": "Activity Monitor",    "Linux": "gnome-system-monitor"},
    "settings":           {"Windows": "ms-settings:",         "Darwin": "System Preferences", "Linux": "gnome-control-center"},
    "powershell":         {"Windows": "powershell.exe",       "Darwin": "Terminal",          "Linux": "bash"},
    "edge":               {"Windows": "msedge",              "Darwin": "Microsoft Edge",    "Linux": "microsoft-edge"},
    "brave":              {"Windows": "brave",               "Darwin": "Brave Browser",     "Linux": "brave-browser"},
    "obsidian":           {"Windows": "Obsidian",             "Darwin": "Obsidian",          "Linux": "obsidian"},
    "notion":             {"Windows": "Notion",              "Darwin": "Notion",           "Linux": "notion"},
    "blender":            {"Windows": "blender",             "Darwin": "Blender",          "Linux": "blender"},
    "capcut":             {"Windows": "CapCut",              "Darwin": "CapCut",           "Linux": "capcut"},
    "postman":            {"Windows": "Postman",             "Darwin": "Postman",          "Linux": "postman"},
    "wiztree":            {"Windows": "WizTree64.exe",          "Darwin": "WizTree",             "Linux": "baobab"},
    "wizz tree":          {"Windows": "WizTree64.exe",          "Darwin": "WizTree",             "Linux": "baobab"},
    "wiz tree":           {"Windows": "WizTree64.exe",          "Darwin": "WizTree",             "Linux": "baobab"},
    "bluestacks":         {"Windows": "HD-Player.exe",          "Darwin": "BlueStacks",          "Linux": "anbox"},
    "free fire":          {"Windows": "HD-Player.exe",          "Darwin": "BlueStacks",          "Linux": "anbox"},
    "figma":              {"Windows": "Figma",                  "Darwin": "Figma",               "Linux": "figma"},
    "womic":              {"Windows": "WOMicClient.exe",        "Darwin": "WOMicClient",          "Linux": "womic"},
    "wo mic":             {"Windows": "WOMicClient.exe",        "Darwin": "WOMicClient",          "Linux": "womic"},
    "wo mic client":      {"Windows": "WOMicClient.exe",        "Darwin": "WOMicClient",          "Linux": "womic"},
    "wc mic":             {"Windows": "WOMicClient.exe",        "Darwin": "WOMicClient",          "Linux": "womic"},
    "wc mic client":      {"Windows": "WOMicClient.exe",        "Darwin": "WOMicClient",          "Linux": "womic"},
}


def _normalize(raw: str) -> str:
    system = platform.system()
    key    = raw.lower().strip()

    # Preference resolution for generic targets
    if any(b in key for b in ["preferred browser", "my browser", "browser", "default browser"]):
        try:
            from memory.memory_manager import get_preference
            pref = get_preference("browser") or get_preference("preferred_browser")
            if pref:
                key = pref.lower().strip()
        except Exception:
            pass

    if any(e in key for e in ["preferred editor", "my editor", "code editor"]):
        try:
            from memory.memory_manager import get_preference
            pref = get_preference("editor") or get_preference("preferred_editor")
            if pref:
                key = pref.lower().strip()
        except Exception:
            pass

    if key in _APP_ALIASES:
        return _APP_ALIASES[key].get(system, raw)
    for alias_key, os_map in _APP_ALIASES.items():
        if alias_key in key or key in alias_key:
            return os_map.get(system, raw)
    return raw



def _is_running(app_name: str) -> bool:
    if not _PSUTIL:
        return True
    app_lower = app_name.lower().replace(" ", "").replace(".exe", "")
    try:
        for proc in psutil.process_iter(["name"]):
            try:
                proc_name = proc.info["name"].lower().replace(" ", "").replace(".exe", "")
                if app_lower in proc_name or proc_name in app_lower:
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception:
        pass
    return False


def _launch_windows(app_name: str) -> bool:
    if app_name.startswith("http://") or app_name.startswith("https://"):
        try:
            webbrowser.open(app_name)
            time.sleep(1.0)
            return True
        except Exception as e:
            print(f"[open_app] Browser open error: {e}")

    # Check if target is a folder shortcut or directory path
    import tempfile
    target_clean = app_name.strip().lower()
    folder_shortcuts = {
        "%temp%":          tempfile.gettempdir(),
        "temp":            tempfile.gettempdir(),
        "temp files":      tempfile.gettempdir(),
        "temporary files": tempfile.gettempdir(),
        "downloads":       str(Path.home() / "Downloads"),
        "documents":       str(Path.home() / "Documents"),
        "desktop":         str(Path.home() / "Desktop"),
        "pictures":        str(Path.home() / "Pictures"),
        "music":           str(Path.home() / "Music"),
        "videos":          str(Path.home() / "Videos"),
    }
    if target_clean in folder_shortcuts:
        fpath = folder_shortcuts[target_clean]
        try:
            subprocess.Popen(["explorer.exe", fpath])
            time.sleep(0.5)
            return True
        except Exception as e:
            print(f"[open_app] Explorer open error: {e}")

    expanded = os.path.expandvars(app_name.strip())
    if os.path.isdir(expanded):
        try:
            subprocess.Popen(["explorer.exe", expanded])
            time.sleep(0.5)
            return True
        except Exception as e:
            print(f"[open_app] Directory open error: {e}")

    # Administrative mode launch
    is_admin = any(adm in app_name.lower() for adm in ["admin", "administrator", "administrative"])
    clean_target = re.sub(r"\b(at\s+)?administr\w+(\s+mode)?\b", "", app_name, flags=re.IGNORECASE).strip()
    target_to_run = clean_target or app_name

    if is_admin:
        try:
            print(f"[open_app] Launching as Administrator: {target_to_run}")
            ps_cmd = f"Start-Process '{target_to_run}' -Verb RunAs"
            r = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, text=True, timeout=5)
            if r.returncode == 0:
                time.sleep(0.8)
                return True
        except Exception as e:
            print(f"[open_app] Admin launch exception: {e}")

    # Direct Windows protocol or executable launch (e.g. ms-settings:, calc.exe, notepad.exe, control, or app command)
    try:
        r = subprocess.run(f'start "" "{target_to_run}"', shell=True, capture_output=True, timeout=2)
        if r.returncode == 0:
            time.sleep(0.5)
            return True
    except Exception:
        pass

    try:
        import pyautogui
        pyautogui.PAUSE = 0.05
        pyautogui.press("win")
        time.sleep(0.3)
        pyautogui.write(target_to_run, interval=0.02)
        time.sleep(0.4)
        if is_admin:
            pyautogui.hotkey("ctrl", "shift", "enter")
        else:
            pyautogui.press("enter")
        time.sleep(0.8)
        return True
    except Exception as e:
        print(f"[open_app] Windows launch failed: {e}")
        return False




def _launch_macos(app_name: str) -> bool:
    if app_name.startswith("http://") or app_name.startswith("https://"):
        try:
            webbrowser.open(app_name)
            time.sleep(1.0)
            return True
        except Exception:
            pass

    try:
        result = subprocess.run(["open", "-a", app_name], capture_output=True, timeout=8)
        if result.returncode == 0:
            time.sleep(1.0)
            return True
    except Exception:
        pass

    try:
        result = subprocess.run(["open", "-a", f"{app_name}.app"], capture_output=True, timeout=8)
        if result.returncode == 0:
            time.sleep(1.0)
            return True
    except Exception:
        pass

    try:
        import pyautogui
        pyautogui.hotkey("command", "space")
        time.sleep(0.6)
        pyautogui.write(app_name, interval=0.05)
        time.sleep(0.8)
        pyautogui.press("enter")
        time.sleep(1.5)
        return True
    except Exception as e:
        print(f"[open_app] macOS Spotlight failed: {e}")
        return False


def _launch_linux(app_name: str) -> bool:
    if app_name.startswith("http://") or app_name.startswith("https://"):
        try:
            webbrowser.open(app_name)
            time.sleep(1.0)
            return True
        except Exception:
            pass

    binary = (
        shutil.which(app_name) or
        shutil.which(app_name.lower()) or
        shutil.which(app_name.lower().replace(" ", "-"))
    )
    if binary:
        try:
            subprocess.Popen([binary], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(1.0)
            return True
        except Exception:
            pass

    try:
        subprocess.run(["xdg-open", app_name], capture_output=True, timeout=5)
        return True
    except Exception:
        pass

    try:
        desktop_name = app_name.lower().replace(" ", "-")
        subprocess.run(["gtk-launch", desktop_name], capture_output=True, timeout=5)
        return True
    except Exception:
        pass

    return False


_OS_LAUNCHERS = {
    "Windows": _launch_windows,
    "Darwin":  _launch_macos,
    "Linux":   _launch_linux,
}


def open_app(
    parameters=None,
    response=None,
    player=None,
    session_memory=None,
    app_name=None,
    **kwargs,
) -> str:
    if app_name:
        app_name = str(app_name).strip()
    elif isinstance(parameters, str):
        app_name = parameters.strip()
    elif isinstance(parameters, dict):
        app_name = (parameters.get("app_name") or parameters.get("name") or "").strip()
    else:
        app_name = ""

    if not app_name:
        return "Please specify which application to open."

    system   = platform.system()
    launcher = _OS_LAUNCHERS.get(system)

    if launcher is None:
        return f"Unsupported OS: {system}"

    normalized = _normalize(app_name)
    print(f"[open_app] Launching: {app_name} -> {normalized} ({system})")

    if player:
        try:
            player.write_log(f"[open_app] {app_name}")
        except Exception:
            pass

    try:
        from actions.action_verifier import verifier
    except Exception:
        verifier = None

    try:
        # Step 1: Initial launch attempt
        launcher(normalized)

        # Step 2: Closed-loop verification
        if verifier:
            v_res = verifier.verify_app_launch(app_name)
            if v_res.status == "SUCCESS":
                try:
                    from memory.memory_manager import record_app_launch
                    record_app_launch(app_name)
                except Exception:
                    pass
                if player:
                    player.write_log(f"[Verifier] {app_name} verified running")
                return f"Opened {app_name} successfully."

            # Step 3: Safe bounded retry if verification failed
            if v_res.status == "FAILURE" and v_res.retry_allowed:
                print(f"[open_app] Verification failed ({v_res.evidence}) -> attempting 1 safe retry")
                if player:
                    player.write_log(f"[Verifier] Retrying launch for {app_name}...")
                
                # Retry with alternative launcher path
                launcher(app_name)
                v_res_retry = verifier.verify_app_launch(app_name, wait_seconds=1.2)
                
                if v_res_retry.status == "SUCCESS":
                    try:
                        from memory.memory_manager import record_app_launch
                        record_app_launch(app_name)
                    except Exception:
                        pass
                    return f"Opened {app_name} successfully."
                else:
                    return f"Tried to open {app_name}, but verified that it is not running."

        # Fallback if verifier unavailable
        try:
            from memory.memory_manager import record_app_launch
            record_app_launch(app_name)
        except Exception:
            pass
        return f"Opened {app_name} successfully."

    except Exception as e:
        print(f"[open_app] Error: {e}")
        return f"Failed to open {app_name}: {e}"

