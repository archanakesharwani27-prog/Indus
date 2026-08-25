#computer_control.py
import io
import json
import re
import string
import subprocess
import sys
import time
import random
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

def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


_BASE         = _base_dir()
_CONFIG_PATH  = _BASE / "config" / "api_keys.json"
_MEMORY_PATH  = _BASE / "memory" / "long_term.json"

def _load_config() -> dict:
    try:
        return json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}

def _get_os() -> str:
    return _load_config().get("os_system", "windows").lower()

_SAFE_SCREENSHOT_ROOTS = (
    Path.home(),
)

def _safe_screenshot_path(requested: str | None) -> Path:
    fallback = Path.home() / "Desktop" / "jarvis_screenshot.png"
    if not requested:
        return fallback
    try:
        p = Path(requested).expanduser().resolve()
        for root in _SAFE_SCREENSHOT_ROOTS:
            if p.is_relative_to(root.resolve()):
                p.parent.mkdir(parents=True, exist_ok=True)
                return p
    except Exception:
        pass
    return fallback

def _require_pyautogui():
    if not _PYAUTOGUI:
        raise RuntimeError("PyAutoGUI not installed. Run: pip install pyautogui")

_FIRST_NAMES = [
    "Alex", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Drew", "Quinn",
    "Avery", "Blake", "Cameron", "Dakota", "Emerson", "Finley", "Harper",
]
_LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
    "Davis", "Wilson", "Moore", "Taylor", "Anderson", "Thomas", "Jackson",
]
_DOMAINS = ["gmail.com", "yahoo.com", "outlook.com", "proton.me", "mail.com"]


def _random_data(data_type: str) -> str:
    dt = data_type.lower().strip()

    if dt == "first_name":
        return random.choice(_FIRST_NAMES)

    if dt == "last_name":
        return random.choice(_LAST_NAMES)

    if dt == "name":
        return f"{random.choice(_FIRST_NAMES)} {random.choice(_LAST_NAMES)}"

    if dt == "email":
        first = random.choice(_FIRST_NAMES).lower()
        last  = random.choice(_LAST_NAMES).lower()
        num   = random.randint(10, 999)
        return f"{first}.{last}{num}@{random.choice(_DOMAINS)}"

    if dt == "username":
        return f"{random.choice(_FIRST_NAMES).lower()}{random.randint(100, 9999)}"

    if dt == "password":
        chars = string.ascii_letters + string.digits + "!@#$%"
        raw   = (
            random.choice(string.ascii_uppercase)
            + random.choice(string.digits)
            + random.choice("!@#$%")
            + "".join(random.choices(chars, k=9))
        )
        return "".join(random.sample(raw, len(raw)))

    if dt == "phone":
        return f"+1{random.randint(200,999)}{random.randint(1_000_000, 9_999_999)}"

    if dt == "birthday":
        y = random.randint(1980, 2000)
        m = random.randint(1, 12)
        d = random.randint(1, 28)
        return f"{m:02d}/{d:02d}/{y}"

    if dt == "address":
        num    = random.randint(100, 9999)
        street = random.choice(["Main St", "Oak Ave", "Park Blvd", "Elm St", "Cedar Ln"])
        return f"{num} {street}"

    if dt == "zip_code":
        return str(random.randint(10000, 99999))

    if dt == "city":
        return random.choice(["New York", "Los Angeles", "Chicago", "Houston", "Phoenix"])

    return f"random_{data_type}_{random.randint(1000, 9999)}"

def _user_profile() -> dict:
    """Read identity fields from long-term memory."""
    try:
        if _MEMORY_PATH.exists():
            data     = json.loads(_MEMORY_PATH.read_text(encoding="utf-8"))
            identity = data.get("identity", {})
            return {k: v.get("value", "") for k, v in identity.items()}
    except Exception:
        pass
    return {}

def _type(text: str, interval: float = 0.03) -> str:
    _require_pyautogui()
    time.sleep(0.3)
    pyautogui.typewrite(text, interval=interval)
    return f"Typed: {text[:60]}{'…' if len(text) > 60 else ''}"


def _smart_type(text: str, clear_first: bool = True) -> str:
    _require_pyautogui()
    if clear_first:
        _clear_field()
        time.sleep(0.1)

    if len(text) > 20 and _PYPERCLIP:
        pyperclip.copy(text)
        time.sleep(0.1)
        pyautogui.hotkey("ctrl", "v")
        return f"Smart-typed (clipboard): {text[:60]}{'…' if len(text) > 60 else ''}"

    pyautogui.typewrite(text, interval=0.04)
    return f"Smart-typed: {text[:60]}{'…' if len(text) > 60 else ''}"


def _click(x=None, y=None, button: str = "left", clicks: int = 1) -> str:
    _require_pyautogui()
    if x is not None and y is not None:
        pyautogui.click(x, y, button=button, clicks=clicks)
        return f"{'Double-c' if clicks == 2 else 'C'}licked ({x}, {y}) [{button}]"
    pyautogui.click(button=button, clicks=clicks)
    return f"Clicked at current position [{button}]"


def _hotkey(*keys) -> str:
    _require_pyautogui()
    pyautogui.hotkey(*keys)
    return f"Hotkey: {'+'.join(keys)}"


def _press(key: str) -> str:
    _require_pyautogui()
    pyautogui.press(key)
    return f"Pressed: {key}"


def _scroll(direction: str = "down", amount: int = 3) -> str:
    _require_pyautogui()

    # Focus the foreground window before scrolling so the event lands correctly
    try:
        import ctypes
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        ctypes.windll.user32.SetForegroundWindow(hwnd)
    except Exception:
        pass

    # Move cursor to center of screen so scroll event hits the active browser/window
    try:
        sw, sh = pyautogui.size()
        cx, cy = sw // 2, (sh // 2) + 50  # slightly below center avoids toolbar
        pyautogui.moveTo(cx, cy, duration=0.08)
        time.sleep(0.05)
    except Exception:
        pass

    # Realistic scroll: pyautogui.scroll() uses WHEEL NOTCHES (each ~3 lines).
    # amount=3 ? 3 notches ? ~9 lines ? natural single scroll action.
    # DO NOT multiply by 240 -- that causes page to jump to end.
    notches = max(1, min(int(amount), 15))  # cap at 15 notches max per call

    if direction in ("down", "bottom"):
        pyautogui.scroll(-notches)
    elif direction in ("up", "top"):
        pyautogui.scroll(notches)
    elif direction == "right":
        pyautogui.hscroll(notches)
    elif direction == "left":
        pyautogui.hscroll(-notches)
    return f"Scrolled {direction} ({notches} notches)"


def _move(x: int, y: int, duration: float = 0.3) -> str:
    _require_pyautogui()
    pyautogui.moveTo(x, y, duration=duration)
    return f"Mouse ? ({x}, {y})"


def _drag(x1: int, y1: int, x2: int, y2: int, duration: float = 0.5) -> str:
    _require_pyautogui()
    pyautogui.moveTo(x1, y1, duration=0.2)
    pyautogui.dragTo(x2, y2, duration=duration, button="left")
    return f"Dragged ({x1},{y1}) ? ({x2},{y2})"


def _clipboard_get() -> str:
    if _PYPERCLIP:
        return pyperclip.paste()
    _hotkey("ctrl", "c")
    time.sleep(0.2)
    return "(copied -- pyperclip unavailable for read)"


def _clipboard_paste(text: str) -> str:
    if _PYPERCLIP:
        pyperclip.copy(text)
        time.sleep(0.1)
        _require_pyautogui()
        pyautogui.hotkey("ctrl", "v")
        return f"Pasted: {text[:60]}{'…' if len(text) > 60 else ''}"
    return "pyperclip not available"


def _screenshot(save_path: str | None = None) -> str:
    _require_pyautogui()
    path = _safe_screenshot_path(save_path)
    img  = pyautogui.screenshot()
    img.save(str(path))
    return f"Screenshot saved: {path}"


def _clear_field() -> str:
    _require_pyautogui()
    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.1)
    pyautogui.press("delete")
    return "Field cleared"

def _focus_window(title: str) -> str:
    os_name = _get_os()

    if os_name == "windows":
        try:
            script = f'(New-Object -ComObject WScript.Shell).AppActivate("{title}")'
            subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                capture_output=True, timeout=5,
            )
            time.sleep(0.3)
            return f"Focused window: {title}"
        except Exception as e:
            return f"focus_window (Windows) failed: {e}"

    if os_name == "mac":
        script = (
            f'tell application "System Events" to '
            f'set frontmost of (first process whose name contains "{title}") to true'
        )
        try:
            subprocess.run(
                ["osascript", "-e", script],
                capture_output=True, timeout=5,
            )
            time.sleep(0.3)
            return f"Focused window: {title}"
        except Exception as e:
            return f"focus_window (macOS) failed: {e}"

    if os_name == "linux":
        try:
            result = subprocess.run(
                ["wmctrl", "-a", title],
                capture_output=True, timeout=5,
            )
            if result.returncode == 0:
                time.sleep(0.3)
                return f"Focused window: {title}"
        except FileNotFoundError:
            pass
        try:
            result = subprocess.run(
                ["xdotool", "search", "--name", title, "windowactivate"],
                capture_output=True, timeout=5,
            )
            time.sleep(0.3)
            return f"Focused window: {title}"
        except FileNotFoundError:
            return "focus_window (Linux) requires wmctrl or xdotool"
        except Exception as e:
            return f"focus_window (Linux) failed: {e}"

    return f"focus_window: unknown OS '{os_name}'"
def _screen_find(description: str, context: str = "") -> tuple[int, int] | None:
    try:
        from actions.vision_engine import ground_ui_element
        res = ground_ui_element(target_description=description, context=context)
        if res.get("found") and not res.get("is_ambiguous") and res.get("confidence", 0.0) >= 0.50:
            cx, cy = int(res["center_x"]), int(res["center_y"])
            print(f"[ComputerControl] Found '{description}' via VisionEngine at ({cx}, {cy}) [conf: {res.get('confidence'):.2f}]")
            return cx, cy
    except Exception as e:
        print(f"[ComputerControl] VisionEngine ground_ui_element error: {e}")

    try:
        import base64
        from or_client import client

        _require_pyautogui()
        w, h  = pyautogui.size()
        img   = pyautogui.screenshot()
        buf   = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode()

        text = client.vision(
            f"This is a screenshot of a {w}×{h} pixel screen. "
            f"Find the UI element: '{description}'. "
            f"Reply ONLY with the center pixel coordinates as: x,y  "
            f"(e.g. 854,423). If not found, reply: NOT_FOUND",
            image_b64=b64,
            mime="image/png",
        )

        if "NOT_FOUND" in text.upper():
            return None

        match = re.search(r"(\d+)\s*,\s*(\d+)", text)
        if match:
            x, y = int(match.group(1)), int(match.group(2))
            margin = 5  # px margin from edge
            if margin <= x <= (w - margin) and margin <= y <= (h - margin):
                print(f"[ComputerControl] Found '{description}' at ({x}, {y})")
                return x, y
            else:
                print(f"[ComputerControl] Coordinates ({x},{y}) out of screen bounds ({w}x{h}) - rejecting")
                return None
    except Exception as e:
        print(f"[ComputerControl] screen_find fallback failed: {e}")
    return None


def computer_control(
    parameters: dict,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    """
    Dispatch table for all computer control actions.

    parameters keys (all optional unless noted):
      action        : (required) one of the actions listed below
      text          : text to type or paste
      x, y          : screen coordinates
      button        : 'left' | 'right' (default: left)
      keys          : hotkey string, e.g. 'ctrl+c'
      key           : single key name, e.g. 'enter'
      direction     : 'up' | 'down' | 'left' | 'right'
      amount        : scroll amount (default: 3)
      seconds       : wait duration
      title         : window title fragment for focus_window
      description   : natural-language element description for screen_find/click
      type          : data type for random_data
      field         : memory field name for user_data
      clear_first   : bool, clear field before typing (default: true)
      path          : save path for screenshot (must be inside home dir)

    Actions:
      type          -- type text at cursor
      smart_type    -- clear field + type (clipboard-backed)
      click         -- left click
      double_click  -- double left click
      right_click   -- right click
      move          -- move mouse
      drag          -- click-drag between two points
      hotkey        -- key combination
      press         -- single key
      scroll        -- scroll the wheel
      copy          -- read clipboard
      paste         -- write + paste clipboard
      screenshot    -- capture screen (safe path only)
      wait          -- sleep N seconds
      clear_field   -- select-all + delete
      focus_window  -- bring window to foreground
      screen_find   -- AI element finder (returns x,y)
      screen_click  -- AI element finder + click
      random_data   -- generate fake form data
      user_data     -- pull real data from memory
    """
    params = parameters or {}
    action = params.get("action", "").lower().strip()

    if not action:
        return "No action specified for computer_control."

    if player:
        player.write_log(f"[Computer] {action}")

    print(f"[ComputerControl] [>] {action}  {params}")

    try:

        if action == "type":
            return _type(params.get("text", ""))

        if action == "smart_type":
            return _smart_type(
                params.get("text", ""),
                clear_first=params.get("clear_first", True),
            )

        if action in ("click", "left_click", "double_click", "right_click"):
            clicks = 2 if action == "double_click" else 1
            btn = "right" if action == "right_click" else "left"
            x = params.get("x")
            y = params.get("y")
            target = params.get("target") or params.get("element") or params.get("description")
            if (x is None or y is None) and target:
                coords = _screen_find(str(target), params.get("context", ""))
                if coords:
                    x, y = coords
                else:
                    return f"Target '{target}' not found or ambiguous on screen. Please clarify location."
            return _click(x, y, btn, clicks)


        if action == "move":
            return _move(int(params.get("x", 0)), int(params.get("y", 0)))

        if action == "drag":
            return _drag(
                int(params.get("x1", 0)), int(params.get("y1", 0)),
                int(params.get("x2", 0)), int(params.get("y2", 0)),
            )

        if action == "hotkey":
            raw  = params.get("keys", "")
            keys = [k.strip() for k in raw.split("+")] if isinstance(raw, str) else raw
            return _hotkey(*keys)

        if action == "press":
            return _press(params.get("key", "enter"))

        if action == "scroll":
            return _scroll(
                direction=params.get("direction", "down"),
                amount=int(params.get("amount", 3)),
            )

        if action == "copy":
            return _clipboard_get()

        if action == "paste":
            return _clipboard_paste(params.get("text", ""))

        if action == "screenshot":
            return _screenshot(params.get("path"))

        if action == "screen_find":
            coords = _screen_find(params.get("description", "") or params.get("target", ""), context=params.get("context", ""))
            return f"{coords[0]},{coords[1]}" if coords else "NOT_FOUND"

        if action in ("vision_click", "click_element"):
            from actions.vision_engine import vision_click
            target = params.get("target") or params.get("description") or params.get("text", "")
            return vision_click(target=target, context=params.get("context", ""), player=player)

        if action == "screen_click":
            desc = params.get("description", "")
            try:
                from actions.action_verifier import verifier
            except Exception:
                verifier = None

            pre_img = verifier.capture_screen_safe() if verifier else None
            coords = _screen_find(desc)
            if coords:
                time.sleep(0.2)
                _click(x=coords[0], y=coords[1])
                time.sleep(0.4)

                # Closed-loop verification
                if verifier and pre_img is not None:
                    post_img = verifier.capture_screen_safe()
                    v_res = verifier.verify_visual_change(pre_img, post_img, action_desc=desc)
                    if v_res.status == "SUCCESS":
                        if player: player.write_log(f"[Verifier] Click verified: '{desc}'")
                        return f"Clicked '{desc}' at {coords} (verified)."
                    elif v_res.status == "FAILURE" and v_res.retry_allowed:
                        # 1 Safe bounded retry
                        if player: player.write_log(f"[Verifier] Retrying click on '{desc}'...")
                        new_coords = _screen_find(desc)
                        if new_coords:
                            _click(x=new_coords[0], y=new_coords[1])
                            return f"Clicked '{desc}' at {new_coords}."

                return f"Clicked '{desc}' at {coords}."
            return f"Element not found on screen: '{desc}'"


        if action == "wait":
            secs = float(params.get("seconds", 1.0))
            secs = min(secs, 30.0)
            time.sleep(secs)
            return f"Waited {secs}s"

        if action == "clear_field":
            return _clear_field()

        if action == "focus_window":
            return _focus_window(params.get("title", ""))

        if action == "random_data":
            dt     = params.get("type", "name")
            result = _random_data(dt)
            print(f"[ComputerControl] random {dt} -> {result}")
            return result

        if action == "user_data":
            field   = params.get("field", "name")
            profile = _user_profile()
            value   = profile.get(field, "")
            if not value:
                value = _random_data(field)
                print(f"[ComputerControl] No '{field}' in memory, using random: {value}")
            return value

        if action in ("volume", "volume_set", "set_volume", "vol", "sound"):
            from actions.computer_settings import computer_settings
            return computer_settings(parameters={"action": "volume_set", "value": params.get("value") or params.get("text") or params.get("level"), "description": params.get("description", "")}, player=player)

        if action in ("volume_up", "vol_up"):
            from actions.computer_settings import volume_up
            volume_up()
            return "Volume increased."

        if action in ("volume_down", "vol_down"):
            from actions.computer_settings import volume_down
            volume_down()
            return "Volume decreased."

        if action in ("kill_process", "kill_app", "close_process", "end_task", "force_close"):
            target = params.get("target") or params.get("name") or params.get("process") or params.get("text", "")
            if not target:
                return "Please specify the app or process name to terminate."
            clean_t = target.strip()
            if not clean_t.lower().endswith(".exe") and not clean_t.isdigit():
                exe_name = f"{clean_t}.exe"
            else:
                exe_name = clean_t

            if _get_os() == "windows":
                if exe_name.isdigit():
                    cmd = ["taskkill", "/F", "/PID", exe_name]
                else:
                    cmd = ["taskkill", "/F", "/IM", exe_name]
                r = subprocess.run(cmd, capture_output=True, text=True)
                if r.returncode == 0:
                    return f"Process '{target}' successfully terminate kar diya gaya hai."
                return f"Taskkill result: {r.stdout.strip() or r.stderr.strip()}"
            else:
                subprocess.run(["pkill", "-f", target], capture_output=True)
                return f"Process '{target}' killed."

        if action in ("system_stats", "system_status", "performance", "specs", "hardware"):
            import psutil
            cpu = psutil.cpu_percent(interval=0.2)
            vmem = psutil.virtual_memory()
            ram_used = vmem.used / (1024**3)
            ram_total = vmem.total / (1024**3)
            # Check disks
            disks_info = []
            for part in psutil.disk_partitions(all=False):
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    free_gb = usage.free / (1024**3)
                    total_gb = usage.total / (1024**3)
                    disks_info.append(f"{part.device} ({free_gb:.1f} GB free of {total_gb:.1f} GB)")
                except Exception:
                    pass
            d_str = ", ".join(disks_info)
            return f"System Telemetry: CPU: {cpu}% load | RAM: {ram_used:.1f}GB / {ram_total:.1f}GB ({vmem.percent}%) | Storage: {d_str}."

        if action in ("minimize_all", "show_desktop"):
            _require_pyautogui()
            pyautogui.hotkey("win", "d")
            return "Desktop shown / All windows minimized."

        if action in ("restart_explorer", "reset_explorer"):
            subprocess.run(["taskkill", "/F", "/IM", "explorer.exe"], capture_output=True)
            time.sleep(0.5)
            subprocess.Popen(["explorer.exe"])
            return "Windows Explorer shell restarted."

        if action in ("empty_recycle_bin", "clean_recycle_bin"):
            from actions.file_controller import empty_recycle_bin
            return empty_recycle_bin()

        if action in ("mute", "unmute", "toggle_mute"):
            from actions.computer_settings import volume_mute
            volume_mute()
            return "Volume mute toggled."

        return f"Unknown action: '{action}'"

    except Exception as e:
        print(f"[ComputerControl] Error in {action}: {e}")
        return f"computer_control '{action}' failed: {e}"