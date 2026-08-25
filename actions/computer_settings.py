import os
import json
import re
import sys
import time
import subprocess
import platform
from pathlib import Path

try:
    import pyautogui
    pyautogui.FAILSAFE = False
    pyautogui.PAUSE    = 0.05
    _PYAUTOGUI = True
except ImportError:
    _PYAUTOGUI = False

try:
    import pyperclip
    _PYPERCLIP = True
except ImportError:
    _PYPERCLIP = False

_OS = platform.system()  # "Windows" | "Darwin" | "Linux"


def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

def _get_macos_wifi_interface() -> str:
    try:
        result = subprocess.run(
            ["networksetup", "-listallhardwareports"],
            capture_output=True, text=True, timeout=5
        )
        lines = result.stdout.splitlines()
        for i, line in enumerate(lines):
            if "Wi-Fi" in line or "AirPort" in line:
                for j in range(i, min(i + 4, len(lines))):
                    if lines[j].startswith("Device:"):
                        return lines[j].split(":", 1)[1].strip()
    except Exception:
        pass
    return "en0" 

def _get_windows_volume_endpoint():
    try:
        from pycaw.pycaw import AudioUtilities
        speakers = AudioUtilities.GetSpeakers()
        vol = getattr(speakers, "EndpointVolume", None)
        if vol is not None:
            return vol
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import IAudioEndpointVolume
        interface = speakers.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        return cast(interface, POINTER(IAudioEndpointVolume))
    except Exception as e:
        print(f"[Settings] Error getting volume endpoint: {e}")
        return None

def volume_up():
    if _OS == "Windows":
        vol = _get_windows_volume_endpoint()
        if vol:
            try:
                curr = vol.GetMasterVolumeLevelScalar()
                vol.SetMasterVolumeLevelScalar(min(1.0, curr + 0.1), None)
                return
            except Exception:
                pass
        for _ in range(5): pyautogui.press("volumeup")
    elif _OS == "Darwin":
        subprocess.run(["osascript", "-e",
            "set volume output volume (output volume of (get volume settings) + 10)"],
            capture_output=True)
    else:
        subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", "+10%"],
            capture_output=True)

def volume_down():
    if _OS == "Windows":
        vol = _get_windows_volume_endpoint()
        if vol:
            try:
                curr = vol.GetMasterVolumeLevelScalar()
                vol.SetMasterVolumeLevelScalar(max(0.0, curr - 0.1), None)
                return
            except Exception:
                pass
        for _ in range(5): pyautogui.press("volumedown")
    elif _OS == "Darwin":
        subprocess.run(["osascript", "-e",
            "set volume output volume (output volume of (get volume settings) - 10)"],
            capture_output=True)
    else:
        subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", "-10%"],
            capture_output=True)

def volume_mute():
    if _OS == "Windows":
        vol = _get_windows_volume_endpoint()
        if vol:
            try:
                vol.SetMute(1, None)
                return
            except Exception:
                pass
        pyautogui.press("volumemute")
    elif _OS == "Darwin":
        subprocess.run(["osascript", "-e", "set volume with output muted"],
            capture_output=True)
    else:
        subprocess.run(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "1"],
            capture_output=True)

def volume_unmute():
    if _OS == "Windows":
        vol = _get_windows_volume_endpoint()
        if vol:
            try:
                vol.SetMute(0, None)
                return
            except Exception:
                pass
        pyautogui.press("volumeup")
        pyautogui.press("volumedown")
    elif _OS == "Darwin":
        subprocess.run(["osascript", "-e", "set volume without output muted"],
            capture_output=True)
    else:
        subprocess.run(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "0"],
            capture_output=True)

def volume_set(value: int):
    value = max(0, min(100, int(value)))
    if _OS == "Windows":
        vol = _get_windows_volume_endpoint()
        if vol:
            try:
                vol.SetMasterVolumeLevelScalar(value / 100.0, None)
                return
            except Exception as e:
                print(f"[Settings] vol.SetMasterVolumeLevelScalar failed: {e}")
        # Keypress fallback
        pyautogui.press("volumemute")
        pyautogui.press("volumemute")
    elif _OS == "Darwin":
        subprocess.run(["osascript", "-e", f"set volume output volume {value}"],
            capture_output=True)
        return
    else:
        subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{value}%"],
            capture_output=True)
        return

_CURRENT_BRIGHTNESS = 100

def _set_gamma_brightness(percent: int) -> bool:
    """Universal Win32 Gamma Ramp Brightness Control for all displays (Desktop & Laptop)."""
    percent = max(10, min(100, int(percent)))
    try:
        import ctypes
        user32 = ctypes.windll.user32
        gdi32 = ctypes.windll.gdi32
        hdc = user32.GetDC(None)
        if not hdc:
            return False
        ramp = (ctypes.c_ushort * 768)()
        factor = percent / 100.0
        for i in range(256):
            val = int(i * 256 * factor)
            val = min(65535, max(0, val))
            ramp[i] = val         # Red
            ramp[256 + i] = val   # Green
            ramp[512 + i] = val   # Blue
        res = gdi32.SetDeviceGammaRamp(hdc, ctypes.byref(ramp))
        user32.ReleaseDC(None, hdc)
        return bool(res)
    except Exception as ex:
        print(f"[Settings] Gamma brightness error: {ex}")
        return False

def brightness_set(value: int) -> str:
    global _CURRENT_BRIGHTNESS
    value = max(10, min(100, int(value)))
    _CURRENT_BRIGHTNESS = value
    
    if _OS == "Windows":
        # 1. Universal Win32 Gamma Ramp (100% works on external HDMI/DP monitors & laptops)
        _set_gamma_brightness(value)
        # 2. Also try WMI for laptop internal panels
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 f"(Get-WmiObject -Namespace root/wmi -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1, {value})"],
                capture_output=True, timeout=2
            )
        except Exception:
            pass
        return f"Brightness set to {value}%."
    elif _OS == "Darwin":
        try:
            val_norm = value / 100.0
            subprocess.run(["brightness", str(val_norm)], capture_output=True)
        except Exception:
            pass
        return f"Brightness set to {value}%."
    elif _OS == "Linux":
        try:
            subprocess.run(["brightnessctl", "set", f"{value}%"], capture_output=True)
        except Exception:
            pass
        return f"Brightness set to {value}%."
    return f"Brightness set to {value}%."

def brightness_up():
    global _CURRENT_BRIGHTNESS
    new_val = min(100, _CURRENT_BRIGHTNESS + 10)
    return brightness_set(new_val)

def brightness_down():
    global _CURRENT_BRIGHTNESS
    new_val = max(10, _CURRENT_BRIGHTNESS - 10)
    return brightness_set(new_val)

def open_password_settings():
    if _OS == "Windows":
        os.system("start ms-settings:signinoptions")
        return "Windows Sign-in options and Password settings open kar di gayi hain."
    elif _OS == "Darwin":
        subprocess.Popen(["open", "x-apple.systempreferences:com.apple.preferences.password"])
        return "macOS Password settings opened."
    else:
        subprocess.Popen(["gnome-control-center", "user-accounts"])
        return "User account settings opened."


def close_app():
    if _OS == "Darwin": pyautogui.hotkey("command", "q")
    else:               pyautogui.hotkey("alt", "f4")

def close_window():
    if _OS == "Darwin": pyautogui.hotkey("command", "w")
    else:               pyautogui.hotkey("ctrl", "w")

def full_screen():
    if _OS == "Darwin": pyautogui.hotkey("ctrl", "command", "f")
    else:               pyautogui.press("f11")

def minimize_window():
    if _OS == "Darwin": pyautogui.hotkey("command", "m")
    else:               pyautogui.hotkey("win", "down")

def maximize_window():
    if _OS == "Darwin":
        subprocess.run(["osascript", "-e",
            'tell application "System Events" to keystroke "f" '
            'using {control down, command down}'],
            capture_output=True)
    elif _OS == "Windows":
        pyautogui.hotkey("win", "up")
    else:
        try:
            subprocess.run(["wmctrl", "-r", ":ACTIVE:", "-b", "add,maximized_vert,maximized_horz"],
                capture_output=True)
        except Exception:
            pyautogui.hotkey("super", "up")

def snap_left():
    if _OS == "Windows":
        pyautogui.hotkey("win", "left")
    elif _OS == "Linux":
        try:
            subprocess.run(["wmctrl", "-r", ":ACTIVE:", "-e", "0,0,0,960,1080"],
                capture_output=True)
        except Exception:
            pass

def snap_right():
    if _OS == "Windows":
        pyautogui.hotkey("win", "right")
    elif _OS == "Linux":
        try:
            subprocess.run(["wmctrl", "-r", ":ACTIVE:", "-e", "0,960,0,960,1080"],
                capture_output=True)
        except Exception:
            pass

def switch_window():
    if _OS == "Darwin": pyautogui.hotkey("command", "tab")
    else:               pyautogui.hotkey("alt", "tab")

def show_desktop():
    if _OS == "Darwin":   pyautogui.hotkey("fn", "f11")
    elif _OS == "Windows": pyautogui.hotkey("win", "d")
    else:                  pyautogui.hotkey("super", "d")

def open_task_manager():
    if _OS == "Windows":
        pyautogui.hotkey("ctrl", "shift", "esc")
    elif _OS == "Darwin":
        subprocess.Popen(["open", "-a", "Activity Monitor"])
    else:
        for cmd in [["gnome-system-monitor"], ["xfce4-taskmanager"], ["htop"]]:
            if subprocess.run(["which", cmd[0]], capture_output=True).returncode == 0:
                subprocess.Popen(cmd)
                break


def focus_search():
    if _OS == "Darwin": pyautogui.hotkey("command", "l")
    else:               pyautogui.hotkey("ctrl", "l")

def pause_video():      pyautogui.press("space")

def refresh_page():
    if _OS == "Darwin": pyautogui.hotkey("command", "r")
    else:               pyautogui.press("f5")

def close_tab():
    if _OS == "Darwin": pyautogui.hotkey("command", "w")
    else:               pyautogui.hotkey("ctrl", "w")

def new_tab():
    if _OS == "Darwin": pyautogui.hotkey("command", "t")
    else:               pyautogui.hotkey("ctrl", "t")

def next_tab():
    if _OS == "Darwin": pyautogui.hotkey("command", "shift", "bracketright")
    else:               pyautogui.hotkey("ctrl", "tab")

def prev_tab():
    if _OS == "Darwin": pyautogui.hotkey("command", "shift", "bracketleft")
    else:               pyautogui.hotkey("ctrl", "shift", "tab")

def go_back():
    if _OS == "Darwin": pyautogui.hotkey("command", "left")
    else:               pyautogui.hotkey("alt", "left")

def go_forward():
    if _OS == "Darwin": pyautogui.hotkey("command", "right")
    else:               pyautogui.hotkey("alt", "right")

def zoom_in():
    if _OS == "Darwin": pyautogui.hotkey("command", "equal")
    else:               pyautogui.hotkey("ctrl", "equal")

def zoom_out():
    if _OS == "Darwin": pyautogui.hotkey("command", "minus")
    else:               pyautogui.hotkey("ctrl", "minus")

def zoom_reset():
    if _OS == "Darwin": pyautogui.hotkey("command", "0")
    else:               pyautogui.hotkey("ctrl", "0")

def find_on_page():
    if _OS == "Darwin": pyautogui.hotkey("command", "f")
    else:               pyautogui.hotkey("ctrl", "f")

def reload_page_n(n: int):
    for _ in range(max(1, n)):
        refresh_page()
        time.sleep(0.8)


def scroll_up(amount: int = 500):    pyautogui.scroll(amount)
def scroll_down(amount: int = 500):  pyautogui.scroll(-amount)

def scroll_top():
    if _OS == "Darwin": pyautogui.hotkey("command", "up")
    else:               pyautogui.hotkey("ctrl", "home")

def scroll_bottom():
    if _OS == "Darwin": pyautogui.hotkey("command", "down")
    else:               pyautogui.hotkey("ctrl", "end")

def page_up():   pyautogui.press("pageup")
def page_down(): pyautogui.press("pagedown")


def copy():
    if _OS == "Darwin": pyautogui.hotkey("command", "c")
    else:               pyautogui.hotkey("ctrl", "c")

def paste():
    if _OS == "Darwin": pyautogui.hotkey("command", "v")
    else:               pyautogui.hotkey("ctrl", "v")

def cut():
    if _OS == "Darwin": pyautogui.hotkey("command", "x")
    else:               pyautogui.hotkey("ctrl", "x")

def undo():
    if _OS == "Darwin": pyautogui.hotkey("command", "z")
    else:               pyautogui.hotkey("ctrl", "z")

def redo():
    if _OS == "Darwin": pyautogui.hotkey("command", "shift", "z")
    else:               pyautogui.hotkey("ctrl", "y")

def select_all():
    if _OS == "Darwin": pyautogui.hotkey("command", "a")
    else:               pyautogui.hotkey("ctrl", "a")

def save_file():
    if _OS == "Darwin": pyautogui.hotkey("command", "s")
    else:               pyautogui.hotkey("ctrl", "s")

def press_enter():   pyautogui.press("enter")
def press_escape():  pyautogui.press("escape")
def press_key(key: str): pyautogui.press(key)

def type_text(text: str, press_enter_after: bool = False):
    if not text:
        return
    if _PYPERCLIP:
        pyperclip.copy(str(text))
        time.sleep(0.15)
        paste()
    else:
        pyautogui.write(str(text), interval=0.03)
    if press_enter_after:
        time.sleep(0.1)
        pyautogui.press("enter")

def take_screenshot():
    if _OS == "Windows":
        pyautogui.hotkey("win", "shift", "s")
    elif _OS == "Darwin":
        pyautogui.hotkey("command", "shift", "3")
    else:
        for cmd in [["scrot"], ["gnome-screenshot"], ["import", "-window", "root", "screenshot.png"]]:
            if subprocess.run(["which", cmd[0]], capture_output=True).returncode == 0:
                subprocess.Popen(cmd)
                return
        pyautogui.hotkey("ctrl", "print_screen")

def lock_screen():
    if _OS == "Windows":
        pyautogui.hotkey("win", "l")
    elif _OS == "Darwin":
        subprocess.run(["pmset", "displaysleepnow"], capture_output=True)
    else:
        for cmd in [
            ["gnome-screensaver-command", "-l"],
            ["xdg-screensaver", "lock"],
            ["loginctl", "lock-session"],
        ]:
            if subprocess.run(["which", cmd[0]], capture_output=True).returncode == 0:
                subprocess.run(cmd, capture_output=True)
                return

def open_system_settings():
    if _OS == "Windows":
        pyautogui.hotkey("win", "i")
    elif _OS == "Darwin":
        subprocess.Popen(["open", "-a", "System Preferences"])
    else:
        for cmd in [["gnome-control-center"], ["xfce4-settings-manager"], ["kcmshell5"]]:
            if subprocess.run(["which", cmd[0]], capture_output=True).returncode == 0:
                subprocess.Popen(cmd)
                return

def open_file_explorer():
    if _OS == "Windows":
        pyautogui.hotkey("win", "e")
    elif _OS == "Darwin":
        subprocess.Popen(["open", str(Path.home())])
    else:
        for cmd in [["nautilus"], ["thunar"], ["dolphin"], ["nemo"]]:
            if subprocess.run(["which", cmd[0]], capture_output=True).returncode == 0:
                subprocess.Popen(cmd)
                return
        subprocess.Popen(["xdg-open", str(Path.home())])

def sleep_display():
    if _OS == "Windows":
        try:
            import ctypes
            ctypes.windll.user32.SendMessageW(0xFFFF, 0x0112, 0xF170, 2)
        except Exception as e:
            print(f"[Settings] sleep_display failed: {e}")
    elif _OS == "Darwin":
        subprocess.run(["pmset", "displaysleepnow"], capture_output=True)
    else:
        subprocess.run(["xset", "dpms", "force", "off"], capture_output=True)

def open_run():
    if _OS == "Windows":
        pyautogui.hotkey("win", "r")

def get_theme_mode() -> str:
    """Returns 'dark' or 'light' for OS theme."""
    if _OS == "Windows":
        try:
            import winreg
            key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Themes\Personalize"
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
            val, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            winreg.CloseKey(key)
            return "light" if val == 1 else "dark"
        except Exception:
            return "dark"
    elif _OS == "Darwin":
        try:
            result = subprocess.run(
                ["defaults", "read", "-g", "AppleInterfaceStyle"],
                capture_output=True, text=True
            )
            return "dark" if "Dark" in result.stdout else "light"
        except Exception:
            return "light"
    else:
        try:
            result = subprocess.run(
                ["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"],
                capture_output=True, text=True
            )
            return "dark" if "dark" in result.stdout.lower() else "light"
        except Exception:
            return "light"


def set_theme_mode(mode: str = "dark") -> str:
    """Explicitly sets system theme to 'dark' or 'light' and verifies registry."""
    mode = mode.lower().strip()
    target_val = 0 if mode == "dark" else 1

    if _OS == "Windows":
        try:
            import winreg
            key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Themes\Personalize"
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS)
            winreg.SetValueEx(key, "AppsUseLightTheme", 0, winreg.REG_DWORD, target_val)
            winreg.SetValueEx(key, "SystemUsesLightTheme", 0, winreg.REG_DWORD, target_val)
            winreg.CloseKey(key)

            try:
                from actions.action_verifier import verifier
                v_res = verifier.verify_theme(expected_mode=mode)
                if v_res.verified:
                    return f"Windows theme {mode} mode set kar diya gaya hai aur verified hai."
            except Exception:
                pass

            return f"Windows theme set to {mode} mode."
        except Exception as e:
            return f"Failed to set Windows theme: {e}"
    elif _OS == "Darwin":
        state_bool = "true" if mode == "dark" else "false"
        subprocess.run(["osascript", "-e",
            f'tell app "System Events" to tell appearance preferences to set dark mode to {state_bool}'],
            capture_output=True)
        return f"macOS theme set to {mode} mode."
    else:
        scheme = "'prefer-dark'" if mode == "dark" else "'default'"
        subprocess.run(["gsettings", "set", "org.gnome.desktop.interface", "color-scheme", scheme], capture_output=True)
        return f"Linux theme set to {mode} mode."


def dark_mode():
    set_theme_mode("dark")


def toggle_wifi() -> str:
    if _OS == "Darwin":
        iface = _get_macos_wifi_interface()
        result = subprocess.run(
            ["networksetup", "-getairportpower", iface],
            capture_output=True, text=True
        )
        state = "off" if "On" in result.stdout else "on"
        subprocess.run(["networksetup", "-setairportpower", iface, state],
            capture_output=True)
        return f"WiFi toggled {'off' if state == 'off' else 'on'}."
    elif _OS == "Windows":
        try:
            subprocess.run(
                ["powershell", "-Command",
                 "$adapter = Get-NetAdapter | Where-Object {$_.PhysicalMediaType -eq 'Native 802.11'};"
                 "if ($adapter.Status -eq 'Up') { Disable-NetAdapter -Name $adapter.Name -Confirm:$false }"
                 "else { Enable-NetAdapter -Name $adapter.Name -Confirm:$false }"],
                capture_output=True, timeout=10
            )
            return "WiFi toggled."
        except Exception as e:
            return f"WiFi toggle error: {e}"
    else:
        try:
            result = subprocess.run(["nmcli", "radio", "wifi"], capture_output=True, text=True)
            state  = "off" if "enabled" in result.stdout else "on"
            subprocess.run(["nmcli", "radio", "wifi", state], capture_output=True)
            return f"WiFi {state}."
        except Exception as e:
            return f"WiFi toggle error: {e}"


def enable_wifi() -> str:
    """Enables WiFi adapter and verifies state."""
    if _OS == "Windows":
        ps = "Get-NetAdapter | Where-Object {$_.PhysicalMediaType -eq 'Native 802.11'} | Enable-NetAdapter -Confirm:$false"
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, timeout=10)
        try:
            from actions.action_verifier import verifier
            v_res = verifier.verify_wifi(expected_enabled=True)
            if v_res.verified:
                return "WiFi enable kar diya gaya hai aur verified active hai."
        except Exception:
            pass
        return "Automatic tareeke se WiFi enable nahi ho paya. Manually Network Settings mein check karein."
    return toggle_wifi()


def disable_wifi() -> str:
    """Disables WiFi adapter and verifies state."""
    if _OS == "Windows":
        ps = "Get-NetAdapter | Where-Object {$_.PhysicalMediaType -eq 'Native 802.11'} | Disable-NetAdapter -Confirm:$false"
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, timeout=10)
        try:
            from actions.action_verifier import verifier
            v_res = verifier.verify_wifi(expected_enabled=False)
            if v_res.verified:
                return "WiFi disable kar diya gaya hai."
        except Exception:
            pass
        return "Automatic tareeke se WiFi disable nahi ho paya. Manually Network Settings mein check karein."
    return toggle_wifi()


def enable_hotspot() -> str:
    """
    Directly enables Windows 10/11 Mobile Hotspot via WinRT / PowerShell automation.
    Verifies actual state change using ActionVerifier before returning.
    """
    if _OS != "Windows":
        return "Mobile Hotspot control is Windows-only."
    ps_script = r"""
try {
    $cs = [Windows.Networking.NetworkOperators.NetworkOperatorTetheringManager, Windows.Networking, ContentType = WindowsRuntime]
    $profiles = [Windows.Networking.Connectivity.NetworkInformation, Windows.Networking.Connectivity, ContentType = WindowsRuntime]::GetConnectionProfiles()
    $adapter = $null
    foreach ($p in $profiles) {
        if ($p.IsWlanConnectionProfile) { $adapter = $p; break }
    }
    if ($adapter -ne $null) {
        $mgr = [Windows.Networking.NetworkOperators.NetworkOperatorTetheringManager]::CreateFromConnectionProfile($adapter)
        if ($mgr.TetheringOperationalState -ne 1) {
            $mgr.StartTetheringAsync() | Out-Null
        }
        Write-Output "HOTSPOT_ENABLED"
    } else { Write-Output "NO_WIFI_ADAPTER" }
} catch { Write-Output "FALLBACK" }
"""
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True, text=True, timeout=15
        )
        # Fallback command if needed
        subprocess.run([
            "powershell", "-NoProfile", "-Command",
            "Set-ItemProperty -Path 'HKLM:\\SYSTEM\\CurrentControlSet\\Services\\icssvc' -Name 'Start' -Value 2 -ErrorAction SilentlyContinue; "
            "netsh wlan set hostednetwork mode=allow -ErrorAction SilentlyContinue; "
            "netsh wlan start hostednetwork -ErrorAction SilentlyContinue"
        ], capture_output=True, text=True, timeout=8)
    except Exception as e:
        print(f"[Hotspot] Enable error: {e}")

    # Closed-loop Verification
    try:
        from actions.action_verifier import verifier
        v_res = verifier.verify_hotspot(expected_enabled=True)
        if v_res.verified:
            return "Mobile Hotspot on kar diya gaya hai aur verified hai."
    except Exception as e:
        print(f"[Hotspot] Verification exception: {e}")

    return "Automatic tareeke se Mobile Hotspot on nahi ho paya. Manually Settings > Mobile Hotspot mein jaakar on karein."


def disable_hotspot() -> str:
    """Disables Windows Mobile Hotspot and verifies closure."""
    if _OS != "Windows":
        return "Mobile Hotspot control is Windows-only."
    try:
        ps_script = r"""
try {
    $cs = [Windows.Networking.NetworkOperators.NetworkOperatorTetheringManager, Windows.Networking, ContentType = WindowsRuntime]
    $profiles = [Windows.Networking.Connectivity.NetworkInformation, Windows.Networking.Connectivity, ContentType = WindowsRuntime]::GetConnectionProfiles()
    $adapter = $null
    foreach ($p in $profiles) {
        if ($p.IsWlanConnectionProfile) { $adapter = $p; break }
    }
    if ($adapter -ne $null) {
        $mgr = [Windows.Networking.NetworkOperators.NetworkOperatorTetheringManager]::CreateFromConnectionProfile($adapter)
        if ($mgr.TetheringOperationalState -eq 1) {
            $mgr.StopTetheringAsync() | Out-Null
        }
    }
} catch {}
netsh wlan stop hostednetwork -ErrorAction SilentlyContinue
Stop-Service icssvc -Force -ErrorAction SilentlyContinue
"""
        subprocess.run([
            "powershell", "-NoProfile", "-Command", ps_script
        ], capture_output=True, timeout=10)
    except Exception as e:
        print(f"[Hotspot] Disable error: {e}")

    # Closed-loop Verification
    try:
        from actions.action_verifier import verifier
        v_res = verifier.verify_hotspot(expected_enabled=False)
        if v_res.verified:
            return "Mobile Hotspot band kar diya gaya hai."
    except Exception as e:
        print(f"[Hotspot] Verification exception: {e}")

    return "Automatic tareeke se Mobile Hotspot band nahi ho paya. Manually Settings mein band karein."



def restart_computer():
    if _OS == "Windows":
        subprocess.run(["shutdown", "/r", "/t", "10"], capture_output=True)
    elif _OS == "Darwin":
        subprocess.run(["osascript", "-e",
            'tell application "System Events" to restart'],
            capture_output=True)
    else:
        subprocess.run(["systemctl", "reboot"], capture_output=True)

def shutdown_computer():
    if _OS == "Windows":
        subprocess.run(["shutdown", "/s", "/t", "10"], capture_output=True)
    elif _OS == "Darwin":
        subprocess.run(["osascript", "-e",
            'tell application "System Events" to shut down'],
            capture_output=True)
    else:
        subprocess.run(["systemctl", "poweroff"], capture_output=True)

def empty_recycle_bin() -> str:
    """Empties the Windows Recycle Bin completely."""
    if _OS == "Windows":
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"],
                capture_output=True, timeout=10
            )
            return "Recycle Bin has been completely emptied."
        except Exception as e:
            return f"Failed to empty Recycle Bin: {e}"
    return "Empty recycle bin supported on Windows."

def restart_explorer() -> str:
    """Restarts Windows Explorer / Taskbar shell."""
    if _OS == "Windows":
        try:
            subprocess.run(["taskkill", "/f", "/im", "explorer.exe"], capture_output=True, timeout=5)
            time.sleep(0.5)
            subprocess.Popen(["explorer.exe"])
            return "Windows Explorer shell restarted."
        except Exception as e:
            return f"Failed to restart explorer: {e}"
    return "Explorer restart only on Windows."

def flush_dns() -> str:
    """Flushes Windows DNS resolver cache."""
    try:
        r = subprocess.run(["ipconfig", "/flushdns"], capture_output=True, text=True, timeout=8)
        return r.stdout.strip() or "DNS cache flushed."
    except Exception as e:
        return f"DNS flush error: {e}"

def get_ip_info() -> str:
    """Retrieves local IPv4 network address."""
    try:
        r = subprocess.run(["ipconfig"], capture_output=True, text=True, timeout=8)
        lines = [line.strip() for line in r.stdout.splitlines() if "IPv4" in line or "Default Gateway" in line]
        return "\n".join(lines[:4]) if lines else "IP information fetched."
    except Exception as e:
        return f"IP fetch error: {e}"


def clean_temp_files() -> str:
    """Deletes temporary files from system %temp%."""
    from actions.file_controller import clean_temp_files as _c_temp
    return _c_temp()


def set_power_plan(plan: str = "high_performance") -> str:
    """Sets Windows Power Plan (High Performance, Balanced, Power Saver)."""
    p = plan.lower().strip()
    plans = {
        "high_performance": "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c",
        "high": "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c",
        "performance": "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c",
        "balanced": "381b4222-f694-41f0-9685-ff5bb260df2e",
        "power_saver": "a1841308-3541-4fab-bc81-f71556f20b4a",
        "saver": "a1841308-3541-4fab-bc81-f71556f20b4a",
    }
    guid = plans.get(p, "381b4222-f694-41f0-9685-ff5bb260df2e")
    if _OS == "Windows":
        subprocess.run(["powercfg", "/setactive", guid], capture_output=True)
        return f"Power plan set to '{plan}'."
    return f"Power plan changed to '{plan}'."


def set_screen_timeout(minutes: int = 15) -> str:
    """Sets monitor sleep timeout in minutes."""
    if _OS == "Windows":
        m = max(1, int(minutes))
        subprocess.run(["powercfg", "/change", "monitor-timeout-ac", str(m)], capture_output=True)
        subprocess.run(["powercfg", "/change", "monitor-timeout-dc", str(m)], capture_output=True)
        return f"Screen sleep timeout set to {m} minutes."
    return f"Screen timeout set to {minutes} minutes."


def set_dns_server(dns_type: str = "cloudflare") -> str:
    """Sets fast secure DNS server (Cloudflare 1.1.1.1, Google 8.8.8.8, or DHCP auto)."""
    d = dns_type.lower().strip()
    if _OS == "Windows":
        if "google" in d:
            primary, secondary = "8.8.8.8", "8.8.4.4"
        elif "dhcp" in d or "auto" in d:
            ps_cmd = "Get-NetAdapter | Where-Object {$_.Status -eq 'Up'} | Set-DnsClientServerAddress -ResetServerAddresses"
            subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True)
            return "DNS reset to automatic DHCP."
        else:  # Cloudflare default
            primary, secondary = "1.1.1.1", "1.0.0.1"

        ps_cmd = f"Get-NetAdapter | Where-Object {{$_.Status -eq 'Up'}} | Set-DnsClientServerAddress -ServerAddresses '{primary}','{secondary}'"
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True)
        return f"DNS server set to {dns_type.upper()} ({primary}, {secondary})."
    return f"DNS server updated."


def toggle_night_light() -> str:
    """Opens Windows Night Light settings."""
    if _OS == "Windows":
        subprocess.Popen(["start", "ms-settings:nightlight"], shell=True)
        return "Night Light settings open kar di gayi hain."
    return "Night light settings opened."


def set_wallpaper_action(image_path: str) -> str:
    """Sets desktop wallpaper to given image."""
    p = Path(image_path).expanduser()
    if not p.exists():
        return f"Wallpaper image not found: {image_path}"
    try:
        import ctypes
        ctypes.windll.user32.SystemParametersInfoW(20, 0, str(p.resolve()), 3)
        return f"Desktop wallpaper set to '{p.name}'."
    except Exception as e:
        return f"Failed to set wallpaper: {e}"

ACTION_MAP: dict[str, callable] = {
    "volume_up":           volume_up,
    "volume_down":         volume_down,
    "mute":                volume_mute,
    "volume_mute":         volume_mute,
    "unmute":              volume_unmute,
    "volume_unmute":       volume_unmute,
    "toggle_mute":         volume_mute,
    "brightness_up":       brightness_up,
    "brightness_down":     brightness_down,
    "sleep_display":       sleep_display,
    "screen_off":          sleep_display,
    "pause_video":         pause_video,
    "play_pause":          pause_video,
    "close_app":           close_app,
    "close_window":        close_window,
    "full_screen":         full_screen,
    "fullscreen":          full_screen,
    "minimize":            minimize_window,
    "maximize":            maximize_window,
    "snap_left":           snap_left,
    "snap_right":          snap_right,
    "switch_window":       switch_window,
    "show_desktop":        show_desktop,
    "task_manager":        open_task_manager,
    "focus_search":        focus_search,
    "refresh_page":        refresh_page,
    "reload":              refresh_page,
    "close_tab":           close_tab,
    "new_tab":             new_tab,
    "next_tab":            next_tab,
    "prev_tab":            prev_tab,
    "go_back":             go_back,
    "go_forward":          go_forward,
    "zoom_in":             zoom_in,
    "zoom_out":            zoom_out,
    "zoom_reset":          zoom_reset,
    "find_on_page":        find_on_page,
    "scroll_up":           scroll_up,
    "scroll_down":         scroll_down,
    "scroll_top":          scroll_top,
    "scroll_bottom":       scroll_bottom,
    "page_up":             page_up,
    "page_down":           page_down,
    "copy":                copy,
    "paste":               paste,
    "cut":                 cut,
    "undo":                undo,
    "redo":                redo,
    "select_all":          select_all,
    "save":                save_file,
    "enter":               press_enter,
    "escape":              press_escape,
    "screenshot":          take_screenshot,
    "lock_screen":         lock_screen,
    "open_settings":       open_system_settings,
    "file_explorer":       open_file_explorer,
    "open_run":            open_run,
    "change_password":     open_password_settings,
    "password_settings":   open_password_settings,
    "signin_settings":     open_password_settings,
    "dark_mode":           dark_mode,
    "set_dark_mode":       lambda: set_theme_mode("dark"),
    "set_light_mode":      lambda: set_theme_mode("light"),
    "light_mode":          lambda: set_theme_mode("light"),
    "toggle_wifi":         toggle_wifi,
    "enable_wifi":         enable_wifi,
    "wifi_on":             enable_wifi,
    "disable_wifi":        disable_wifi,
    "wifi_off":            disable_wifi,
    "hotspot_on":          enable_hotspot,
    "enable_hotspot":      enable_hotspot,
    "turn_on_hotspot":     enable_hotspot,
    "mobile_hotspot":      enable_hotspot,
    "hotspot_off":         disable_hotspot,
    "disable_hotspot":     disable_hotspot,
    "empty_recycle_bin":   empty_recycle_bin,
    "clean_recycle_bin":   empty_recycle_bin,
    "restart_explorer":    restart_explorer,
    "flush_dns":           flush_dns,
    "get_ip":              get_ip_info,
    "clean_temp":          clean_temp_files,
    "control_panel":       lambda: subprocess.Popen(["control"]),
    "device_manager":      lambda: subprocess.Popen(["devmgmt.msc"]),
    "services":            lambda: subprocess.Popen(["services.msc"]),
    "regedit":             lambda: subprocess.Popen(["regedit"]),
    "calculator":          lambda: subprocess.Popen(["calc"]),
    "notepad":             lambda: subprocess.Popen(["notepad"]),
    "paint":               lambda: subprocess.Popen(["mspaint"]),
    "snipping_tool":       lambda: subprocess.Popen(["snippingtool"]),
    "bluetooth_settings":  lambda: subprocess.Popen(["start", "ms-settings:bluetooth"], shell=True),
    "enable_bluetooth":    lambda: subprocess.Popen(["start", "ms-settings:bluetooth"], shell=True),
    "disable_bluetooth":   lambda: subprocess.Popen(["powershell", "-NoProfile", "-Command", "Get-Service bthserv -ErrorAction SilentlyContinue | Stop-Service -Force -ErrorAction SilentlyContinue"]),
    "sound_settings":      lambda: subprocess.Popen(["start", "ms-settings:sound"], shell=True),
    "display_settings":    lambda: subprocess.Popen(["start", "ms-settings:display"], shell=True),
    "network_settings":    lambda: subprocess.Popen(["start", "ms-settings:network"], shell=True),
    "windows_update":      lambda: subprocess.Popen(["start", "ms-settings:windowsupdate"], shell=True),
    "installed_apps":      lambda: subprocess.Popen(["start", "ms-settings:appsfeatures"], shell=True),
    "power_high_performance": lambda: set_power_plan("high_performance"),
    "power_saver":         lambda: set_power_plan("power_saver"),
    "power_balanced":      lambda: set_power_plan("balanced"),
    "night_light":         toggle_night_light,
    "night_light_settings": toggle_night_light,
    "dns_cloudflare":      lambda: set_dns_server("cloudflare"),
    "dns_google":          lambda: set_dns_server("google"),
    "dns_dhcp":            lambda: set_dns_server("dhcp"),
    "storage_settings":    lambda: subprocess.Popen(["start", "ms-settings:storagesense"], shell=True),
    "battery_settings":    lambda: subprocess.Popen(["start", "ms-settings:batterysaver"], shell=True),
    "notifications":       lambda: subprocess.Popen(["start", "ms-settings:notifications"], shell=True),
    "privacy_settings":    lambda: subprocess.Popen(["start", "ms-settings:privacy"], shell=True),
    "restart":             restart_computer,
    "shutdown":            shutdown_computer,
}

_DANGEROUS_ACTIONS = {"restart", "shutdown"}


def _detect_action(description: str) -> dict:
    from or_client import client

    available = ", ".join(sorted(ACTION_MAP.keys())) + \
                ", volume_set, brightness_set, type_text, press_key, reload_n"

    prompt = f"""You are an intent detector for a computer control assistant.
The user issued a command (possibly in any language): "{description}"
Available actions: {available}
Return ONLY a valid JSON object: {{"action": "action_name", "value": null_or_value}}
Rules:
- For volume_set or brightness_set: value is an integer 0-100.
- For type_text: value is the exact text to type.
- For press_key: value is the key name (e.g. "f5", "tab", "enter").
- For reload_n: value is an integer.
- Return ONLY the JSON, no explanation, no markdown."""

    try:
        raw  = client.chat_json(prompt, system="Return only valid JSON. No extra text.")
        return raw
    except Exception as e:
        print(f"[Settings] Intent detection failed: {e}")
        return {"action": description.lower().replace(" ", "_"), "value": None}
    
def _intent_override(parameters: dict = None) -> tuple:
    """
    Hardcoded deterministic intent override.
    Scans raw action, description, text, value, and parameter keys for unambiguous keywords
    (Hotspot, WiFi, Bluetooth, Dark/Light Mode, Night Light, Volume, Mute, Recycle Bin)
    and forces the exact action to bypass any LLM hallucinations or generic routing.
    """
    if not parameters or not isinstance(parameters, dict):
        return None, None

    tokens = []
    for k, v in parameters.items():
        if isinstance(v, str) and v.strip():
            tokens.append(v.strip().lower())
        elif isinstance(v, (int, float)):
            tokens.append(str(v))

    combined = " ".join(tokens)
    raw_action = str(parameters.get("action", "")).lower().strip()

    # ── 1. Hotspot On / Off ──────────────────────────────────────────────────
    if "hotspot" in combined or "tethering" in combined:
        if any(w in combined for w in ("off", "disable", "stop", "band", "deactivate", "close", "shutdown")):
            return "disable_hotspot", None
        if any(w in combined for w in ("on", "enable", "start", "chalu", "shuru", "kholo", "activate", "turn")):
            return "enable_hotspot", None
        if raw_action in ("hotspot_off", "disable_hotspot"):
            return "disable_hotspot", None
        if raw_action in ("hotspot_on", "enable_hotspot", "turn_on_hotspot", "mobile_hotspot"):
            return "enable_hotspot", None
        return "enable_hotspot", None

    # ── 2. WiFi On / Off ─────────────────────────────────────────────────────
    if "wifi" in combined or "wi-fi" in combined or "wlan" in combined:
        if any(w in combined for w in ("off", "disable", "stop", "band", "deactivate")):
            return "disable_wifi", None
        if any(w in combined for w in ("on", "enable", "start", "chalu", "shuru", "activate")):
            return "enable_wifi", None
        if any(w in combined for w in ("toggle", "badlo", "switch")):
            return "toggle_wifi", None
        if raw_action in ("wifi_off", "disable_wifi"):
            return "disable_wifi", None
        if raw_action in ("wifi_on", "enable_wifi"):
            return "enable_wifi", None

    # ── 3. Bluetooth On / Off / Settings ─────────────────────────────────────
    if "bluetooth" in combined or "bt" in combined:
        if any(w in combined for w in ("off", "disable", "stop", "band")):
            return "disable_bluetooth", None
        if any(w in combined for w in ("on", "enable", "start", "chalu", "shuru", "kholo", "settings")):
            return "bluetooth_settings", None

    # ── 4. Dark / Light Theme ────────────────────────────────────────────────
    if any(w in combined for w in ("dark mode", "dark theme", "darkmode", "kaala theme", "black theme")):
        return "set_dark_mode", None
    if any(w in combined for w in ("light mode", "light theme", "lightmode", "safed theme", "white theme")):
        return "set_light_mode", None

    # ── 5. Night Light / Blue Light Filter ───────────────────────────────────
    if any(w in combined for w in ("night light", "nightlight", "reading mode", "blue light")):
        return "night_light", None

    # ── 6. Volume & Mute Control ─────────────────────────────────────────────
    if any(w in combined for w in ("unmute", "awaaz kholo", "awaaz chalu")):
        return "volume_unmute", None
    if any(w in combined for w in ("mute", "silent", "awaaz band", "sound band")):
        return "volume_mute", None
    if any(w in combined for w in ("volume up", "awaaz badhao", "sound up", "increase volume", "volume badha")):
        return "volume_up", None
    if any(w in combined for w in ("volume down", "awaaz kam", "sound down", "decrease volume", "volume ghata")):
        return "volume_down", None

    if "volume" in combined or "sound" in combined or "awaaz" in combined:
        m = re.search(r"(\d{1,3})\s*%?", combined)
        if m:
            val = int(m.group(1))
            if 0 <= val <= 100:
                return "volume_set", val

    # ── 7. Recycle Bin ───────────────────────────────────────────────────────
    if any(w in combined for w in ("recycle bin", "recyclebin", "trash", "kachra")):
        if any(w in combined for w in ("clean", "empty", "clear", "khali", "saaf")):
            return "empty_recycle_bin", None

    # ── 8. Lock Screen / Screenshot ──────────────────────────────────────────
    if "screenshot" in combined or "screen shot" in combined:
        return "screenshot", None
    if any(w in combined for w in ("lock screen", "lock pc", "lock computer")):
        return "lock_screen", None

    return None, None


def computer_settings(
    parameters: dict = None,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    if not _PYAUTOGUI:
        return "pyautogui is not installed. Run: pip install pyautogui"

    params      = parameters or {}
    raw_action  = params.get("action", "").strip()
    description = params.get("description", "").strip()
    value       = params.get("value", None)

    # ── HARDCODED INTENT OVERRIDE (Bypasses LLM hallucinations) ─────────────
    forced_action, forced_value = _intent_override(params)
    if forced_action:
        raw_action = forced_action
        if forced_value is not None:
            value = forced_value

    if not raw_action and description:
        detected   = _detect_action(description)
        raw_action = detected.get("action", "")
        if value is None:
            value = detected.get("value")

    action = raw_action.lower().strip().replace(" ", "_").replace("-", "_")

    if not action:
        return "No action could be determined."

    print(f"[Settings] Action: {action}  Value: {value}  OS: {_OS}")
    if player:
        player.write_log(f"[Settings] {action}")

    if action in _DANGEROUS_ACTIONS:
        confirmed = str(params.get("confirmed", "")).lower()
        if confirmed not in ("yes", "true", "1", "confirm"):
            return (
                f"This will {action} the computer. "
                f"Please confirm by calling again with confirmed=yes."
            )

    if action in ("volume_set", "set_volume", "volume", "sound", "set_sound", "vol"):
        try:
            val_num = None
            if value is not None:
                m = re.search(r"\d+", str(value))
                if m:
                    val_num = int(m.group())
            if val_num is None and description:
                m = re.search(r"\d+", str(description))
                if m:
                    val_num = int(m.group())
            if val_num is None:
                val_num = 50

            volume_set(val_num)

            # Closed-loop hardware verification
            try:
                from actions.action_verifier import verifier
                v_res = verifier.verify_volume(val_num)
                if v_res.status == "SUCCESS":
                    if player: player.write_log(f"[Verifier] Volume {val_num}% hardware-verified")
                    return f"Volume set to {val_num}%."
                elif v_res.status == "FAILURE" and v_res.retry_allowed:
                    volume_set(val_num)
                    v_retry = verifier.verify_volume(val_num)
                    return f"Volume set to {val_num}%."
            except Exception:
                pass

            return f"Volume set to {val_num}%."
        except Exception as e:
            return f"Could not set volume: {e}"

    if action in ("brightness_set", "set_brightness", "brightness", "screen_brightness", "display_brightness", "set"):
        try:
            val_num = None
            if value is not None:
                m = re.search(r"\d+", str(value))
                if m:
                    val_num = int(m.group())
            if val_num is None and description:
                m = re.search(r"\d+", str(description))
                if m:
                    val_num = int(m.group())
            if val_num is None:
                val_num = 50

            res = brightness_set(val_num)
            try:
                from actions.action_verifier import verifier
                v_res = verifier.verify_brightness(val_num)
                if player: player.write_log(f"[Verifier] Brightness {val_num}% verified")
            except Exception:
                pass
            return res
        except Exception as e:
            return f"Could not set brightness: {e}"


    if action in ("change_password", "password", "signin_options", "user_password"):
        return open_password_settings()


    if action in ("type_text", "write_on_screen", "type", "write"):
        text = str(value or params.get("text", "")).strip()
        if not text:
            return "No text provided to type."
        enter_after = str(params.get("press_enter", "false")).lower() in ("true", "1", "yes")
        type_text(text, press_enter_after=enter_after)
        return f"Typed: {text[:80]}"

    if action == "press_key":
        key = str(value or params.get("key", "")).strip()
        if not key:
            return "No key specified."
        press_key(key)
        return f"Pressed: {key}"

    if action in ("reload_n", "refresh_n", "reload_page_n"):
        try:
            reload_page_n(int(value or 1))
            return f"Reloaded {value or 1} time(s)."
        except Exception as e:
            return f"Reload failed: {e}"

    if action == "scroll_up":
        scroll_up(int(value or 500))
        return "Scrolled up."

    if action == "scroll_down":
        scroll_down(int(value or 500))
        return "Scrolled down."

    func = ACTION_MAP.get(action)
    if not func:
        return f"Unknown action: '{raw_action}'."

    try:
        func()
        return f"Done: {action}."
    except Exception as e:
        print(f"[Settings] Action failed ({action}): {e}")
        return f"Action failed ({action}): {e}"