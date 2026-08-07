"""
AppLauncher - Find and launch installed Windows applications
"""

import os
import re
import subprocess
import winreg
from typing import Dict, List, Optional
from dataclasses import dataclass


class AppLauncher:
    """Discover and launch Windows applications."""
    
    def __init__(self):
        self._app_cache: Dict[str, str] = {}
        self._cache_built = False
    
    def build_cache(self) -> None:
        """Build application cache from registry and PATH."""
        if self._cache_built:
            return
        
        apps = {}
        
        # 1. Scan PATH directories
        paths = os.environ.get("PATH", "").split(os.pathsep)
        for path in paths:
            try:
                if os.path.isdir(path):
                    for file in os.listdir(path):
                        if file.lower().endswith((".exe", ".bat", ".cmd")):
                            name = os.path.splitext(file)[0].lower()
                            if name not in apps:
                                apps[name] = os.path.join(path, file)
            except (PermissionError, OSError):
                pass
        
        # 2. Scan registry (HKLM and HKCU)
        registry_paths = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"),
        ]
        
        for hkey, subkey in registry_paths:
            try:
                with winreg.OpenKey(hkey, subkey) as key:
                    i = 0
                    while True:
                        try:
                            app_key_name = winreg.EnumKey(key, i)
                            i += 1
                            
                            with winreg.OpenKey(key, app_key_name) as app_key:
                                try:
                                    path, _ = winreg.QueryValueEx(app_key, "")
                                    if path and os.path.exists(path):
                                        name = os.path.splitext(app_key_name)[0].lower()
                                        if name not in apps:
                                            apps[name] = path
                                except (FileNotFoundError, OSError):
                                    pass
                        except OSError:
                            break
            except (FileNotFoundError, PermissionError):
                pass
        
        # 3. Scan Start Menu
        start_menu_paths = [
            os.path.join(os.environ.get("PROGRAMDATA", ""), r"Microsoft\Windows\Start Menu\Programs"),
            os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs"),
        ]
        
        for start_path in start_menu_paths:
            try:
                for root, dirs, files in os.walk(start_path):
                    for file in files:
                        if file.lower().endswith(".lnk"):
                            name = os.path.splitext(file)[0].lower()
                            if name not in apps:
                                lnk_path = os.path.join(root, file)
                                apps[name] = lnk_path
            except (PermissionError, OSError):
                pass
        
        # 4. Common app mappings (fallback)
        common_apps = {
            "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            "chrome": r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            "firefox": r"C:\Program Files\Mozilla Firefox\firefox.exe",
            "edge": r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            "code": r"C:\Users\%USERNAME%\AppData\Local\Programs\Microsoft VS Code\Code.exe",
            "vscode": r"C:\Users\%USERNAME%\AppData\Local\Programs\Microsoft VS Code\Code.exe",
            "notepad": "notepad.exe",
            "calc": "calc.exe",
            "calculator": "calc.exe",
            "explorer": "explorer.exe",
            "cmd": "cmd.exe",
            "powershell": "powershell.exe",
            "wt": "wt.exe",
            "terminal": "wt.exe",
            "whatsapp": r"C:\Users\%USERNAME%\AppData\Local\WhatsApp\WhatsApp.exe",
            "teams": r"C:\Users\%USERNAME%\AppData\Local\Microsoft\Teams\current\Teams.exe",
            "discord": r"C:\Users\%USERNAME%\AppData\Local\Discord\app-*\Discord.exe",
            "spotify": r"C:\Users\%USERNAME%\AppData\Roaming\Spotify\Spotify.exe",
            "vlc": r"C:\Program Files\VideoLAN\VLC\vlc.exe",
            "paint": "mspaint.exe",
            "word": r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE",
            "excel": r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE",
            "powerpoint": r"C:\Program Files\Microsoft Office\root\Office16\POWERPNT.EXE",
            "outlook": r"C:\Program Files\Microsoft Office\root\Office16\OUTLOOK.EXE",
            "settings": "ms-settings:",
            "control": "control.exe",
            "taskmgr": "taskmgr.exe",
        }
        
        for name, path in common_apps.items():
            if name not in apps:
                expanded = os.path.expandvars(path)
                if os.path.exists(expanded) or path.startswith("ms-"):
                    apps[name] = expanded
        
        self._app_cache = apps
        self._cache_built = True
        print(f"AppLauncher: Cached {len(apps)} applications")
    
    def find_app(self, name: str) -> Optional[str]:
        """Find application executable path by name."""
        if not self._cache_built:
            self.build_cache()
        
        name_lower = name.lower().strip()
        
        # Direct match
        if name_lower in self._app_cache:
            return self._app_cache[name_lower]
        
        # Fuzzy match - more conservative: only match if search term is a word prefix
        # or if cached name starts with search term
        for cached_name, path in self._app_cache.items():
            # Match if search term is prefix of cached name
            if cached_name.startswith(name_lower):
                return path
            # Match if cached name contains search term as whole word (separated by _, -, space)
            if f"_{name_lower}_" in f"_{cached_name}_" or f"-{name_lower}-" in f"-{cached_name}-" or f" {name_lower} " in f" {cached_name} ":
                return path
        
        return None
    
    def launch(self, name: str, arguments: str = "") -> str:
        """Launch application by name."""
        path = self.find_app(name)
        
        if not path:
            return f"Application not found: {name}"
        
        # Handle Windows URIs (ms-settings:, etc.)
        if path.startswith("ms-") or path.startswith("http"):
            try:
                subprocess.Popen(["start", "", path], shell=True)
                return f"Opened {name}"
            except Exception as e:
                return f"Failed to open {name}: {e}"
        
        # Handle .lnk files
        if path.endswith(".lnk"):
            try:
                subprocess.Popen(["cmd", "/c", "start", "", path], shell=True)
                return f"Launched {name}"
            except Exception as e:
                return f"Failed to launch {name}: {e}"
        
        # Regular executable
        try:
            if arguments:
                subprocess.Popen([path] + arguments.split(), shell=False)
            else:
                subprocess.Popen([path], shell=False)
            return f"Launched {name}"
        except FileNotFoundError:
            # Try with shell=True for PATH lookup
            try:
                cmd = f'"{path}" {arguments}' if arguments else f'"{path}"'
                subprocess.Popen(cmd, shell=True)
                return f"Launched {name}"
            except Exception as e:
                return f"Failed to launch {name}: {e}"
        except Exception as e:
            return f"Error launching {name}: {e}"
    
    def list_apps(self, filter_str: str = "") -> List[str]:
        """List cached applications, optionally filtered."""
        if not self._cache_built:
            self.build_cache()
        
        apps = list(self._app_cache.keys())
        if filter_str:
            filter_lower = filter_str.lower()
            apps = [a for a in apps if filter_lower in a]
        return sorted(apps)


# Global instance
_launcher = AppLauncher()


def get_launcher() -> AppLauncher:
    return _launcher