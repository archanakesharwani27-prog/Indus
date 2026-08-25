# actions/mobile_bridge.py
# INDUS Android ADB Wireless Bridge
# Prerequisites: Android phone with USB debugging + adb tcpip 5555
import re, subprocess, shutil

def _adb(args: list, timeout: int = 10) -> str:
    adb = shutil.which("adb") or "adb"
    try:
        r = subprocess.run([adb] + args, capture_output=True, text=True, timeout=timeout)
        return (r.stdout + r.stderr).strip()
    except FileNotFoundError:
        return "ADB not found. Install Android Platform Tools and add to PATH."
    except subprocess.TimeoutExpired:
        return f"ADB command timed out after {timeout}s."
    except Exception as e:
        return f"ADB error: {e}"

def connect_phone(ip_address: str, port: int = 5555, player=None) -> str:
    if not ip_address:
        return "IP address required. Find it in Phone Settings > About > IP Address."
    result = _adb(["connect", f"{ip_address}:{port}"])
    if player: player.write_log(f"[ADB] connect {ip_address}:{port} -> {result[:50]}")
    if "connected" in result.lower():
        return f"Phone connected at {ip_address}:{port}. ADB bridge ready."
    return f"Connection attempt: {result}"

def make_phone_call(phone_number: str, player=None) -> str:
    if not phone_number: return "Phone number required."
    number = re.sub(r"[\s\-\(\)]", "", phone_number)
    result = _adb(["shell", "am", "start", "-a", "android.intent.action.CALL", "-d", f"tel:{number}"])
    if player: player.write_log(f"[ADB] Calling {number}")
    if "error" in result.lower() or "exception" in result.lower():
        return f"Call failed: {result}"
    return f"Calling {phone_number} on your phone now."

def send_phone_sms(phone_number: str, message: str, player=None) -> str:
    if not phone_number or not message:
        return "Phone number and message are required."
    number = re.sub(r"[\s\-\(\)]", "", phone_number)
    result = _adb(["shell", "am", "start", "-a", "android.intent.action.SENDTO",
                   "-d", f"smsto:{number}", "--es", "sms_body", message,
                   "--ez", "exit_on_sent", "true"])
    if player: player.write_log(f"[ADB] SMS to {number}")
    return f"SMS compose screen opened for {phone_number}."

def get_phone_status(player=None) -> str:
    battery = _adb(["shell", "dumpsys", "battery"])
    wifi = _adb(["shell", "dumpsys", "wifi"])
    level, charging, wifi_name = "Unknown", "Unknown", "Unknown"
    for line in battery.splitlines():
        if "level:" in line: level = line.split(":")[-1].strip() + "%"
        if "status:" in line:
            charging = "Charging" if line.split(":")[-1].strip() == "2" else "Discharging"
    m = re.search(r"SSID: ([^,]+)", wifi)
    if m: wifi_name = m.group(1).strip()
    if player: player.write_log(f"[ADB] Status: bat={level}, {charging}")
    return f"Phone: Battery {level}, {charging}. Wi-Fi: {wifi_name}."

def mobile_bridge(parameters: dict, player=None) -> str:
    from core.cancellation import cancellation_manager
    import shutil as _shutil

    if cancellation_manager.is_cancelled():
        return "Mobile bridge operation cancelled by user."

    # Check ADB availability upfront and return ENVIRONMENT_UNAVAILABLE (not a failure)
    if not _shutil.which("adb"):
        msg = "[ENVIRONMENT_UNAVAILABLE] ADB not found. Install Android Platform Tools and add to PATH."
        if player:
            player.write_log("[ADB] NOT AVAILABLE")
        return msg

    action = (parameters or {}).get("action", "")
    if action == "connect": return connect_phone(parameters.get("ip_address",""), parameters.get("port", 5555), player)
    if action == "call":    return make_phone_call(parameters.get("phone_number",""), player)
    if action == "sms":     return send_phone_sms(parameters.get("phone_number",""), parameters.get("message",""), player)
    if action == "status":  return get_phone_status(player)
    return f"Unknown action: {action}. Use: connect | call | sms | status"
