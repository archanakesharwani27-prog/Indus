"""
Bluetooth Controller Module for INDUS (INDUS)
Autonomous Bluetooth device discovery, connection, disconnection, and radio control on Windows.
"""

from __future__ import annotations

import json
import os
import platform
import re
import subprocess
import time
from typing import Any, Dict, List, Optional

_OS = platform.system()


def _normalize_name(name: str) -> str:
    """Normalize device name for fuzzy matching (remove dashes, spaces, lowercase)."""
    return re.sub(r"[^a-zA-Z0-9]", "", name or "").lower()


def list_bluetooth_devices(only_connected: bool = False) -> List[Dict[str, Any]]:
    """
    List all paired and connected Bluetooth devices on the system.
    Returns a cleaned list of unique devices (deduplicated).
    """
    if _OS != "Windows":
        return []

    ps_cmd = """
    $devs = Get-PnpDevice -Class Bluetooth -ErrorAction SilentlyContinue | ForEach-Object {
        [PSCustomObject]@{
            FriendlyName = $_.FriendlyName
            Status       = $_.Status
            InstanceId   = $_.InstanceId
            Present      = $_.Present
        }
    }
    $devs | ConvertTo-Json -Depth 2
    """
    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            capture_output=True,
            text=True,
            timeout=8
        )
        if not res.stdout.strip():
            return []

        raw_data = json.loads(res.stdout)
        if isinstance(raw_data, dict):
            raw_data = [raw_data]

        devices: Dict[str, Dict[str, Any]] = {}

        ignored_patterns = [
            r"microsoft bluetooth",
            r"rfcomm",
            r"personal area network",
            r"sim access",
            r"phonebook access",
            r"object push",
            r"headset audio gateway",
            r"generic bluetooth radio",
        ]

        for item in raw_data:
            name = (item.get("FriendlyName") or "").strip()
            if not name:
                continue

            name_lower = name.lower()
            if any(re.search(pat, name_lower) for pat in ignored_patterns):
                continue

            instance_id = item.get("InstanceId") or ""
            present = bool(item.get("Present", False))
            status = item.get("Status", "Unknown")

            clean_name = re.sub(r"\s+Avrcp\s+Transport.*$", "", name, flags=re.IGNORECASE).strip()
            norm_key = _normalize_name(clean_name)

            is_connected = (status == "OK" and present)

            if norm_key not in devices or (is_connected and not devices[norm_key]["connected"]):
                devices[norm_key] = {
                    "name": clean_name,
                    "status": "Connected" if is_connected else ("Disabled" if status == "Error" else "Disconnected"),
                    "connected": is_connected,
                    "instance_id": instance_id,
                }

        results = list(devices.values())
        if only_connected:
            results = [d for d in results if d["connected"]]
        return results

    except Exception as e:
        print(f"[Bluetooth] Error listing devices: {e}")
        return []


def _find_matching_device(device_name: str) -> Optional[Dict[str, Any]]:
    """Fuzzy find a Bluetooth device by name or keyword."""
    if not device_name:
        return None

    norm_target = _normalize_name(device_name)
    all_devs = list_bluetooth_devices(only_connected=False)

    # 1. Exact normalized match
    for d in all_devs:
        if _normalize_name(d["name"]) == norm_target:
            return d

    # 2. Substring match
    for d in all_devs:
        norm_d = _normalize_name(d["name"])
        if norm_target in norm_d or norm_d in norm_target:
            return d

    # 3. Token overlap match
    target_tokens = set(re.findall(r"[a-zA-Z0-9]+", device_name.lower()))
    for d in all_devs:
        dev_tokens = set(re.findall(r"[a-zA-Z0-9]+", d["name"].lower()))
        if target_tokens and (target_tokens.issubset(dev_tokens) or dev_tokens.issubset(target_tokens)):
            return d

    return None


def disconnect_bluetooth_device(device_name: str) -> str:
    """
    Disconnects a specific Bluetooth device by name dynamically on any Windows PC.
    Works for any brand (Sony, Apple, Bose, Boat, OnePlus, Realme, JBL, Samsung, etc.).
    """
    if _OS != "Windows":
        return "Bluetooth device management is only supported on Windows in this build."

    target = _find_matching_device(device_name)
    if not target:
        all_devs = list_bluetooth_devices()
        dev_names = ", ".join([f"'{d['name']}'" for d in all_devs[:6]])
        return (
            f"Could not find Bluetooth device matching '{device_name}'. "
            f"Available paired devices on this system: {dev_names if dev_names else 'None found'}."
        )

    matched_name = target["name"]
    inst_id = target.get("instance_id", "")

    # Extract hardware MAC/DEV key (e.g. DEV_XXXXXXXXXXXX) or match full name/instance
    dev_match = re.search(r"DEV_([0-9A-F]{12})", inst_id, re.IGNORECASE)
    if dev_match:
        dev_filter = f"$_.InstanceId -match '{dev_match.group(1)}'"
    else:
        escaped_name = re.escape(matched_name)
        dev_filter = f"$_.FriendlyName -match '{escaped_name}' -or $_.InstanceId -eq '{inst_id}'"

    ps_disconnect = f"""
    $matched = Get-PnpDevice -Class Bluetooth -ErrorAction SilentlyContinue | Where-Object {{
        {dev_filter}
    }}
    foreach ($d in $matched) {{
        Disable-PnpDevice -InstanceId $d.InstanceId -Confirm:$false -ErrorAction SilentlyContinue
    }}
    """
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_disconnect],
            capture_output=True,
            text=True,
            timeout=8
        )
        print(f"[Bluetooth] Dynamic disconnect executed for: {matched_name}")
        return f"Bluetooth device '{matched_name}' disconnected successfully."
    except Exception as e:
        print(f"[Bluetooth] Error disconnecting device {matched_name}: {e}")
        return f"Failed to disconnect '{matched_name}': {e}"


def connect_bluetooth_device(device_name: str) -> str:
    """
    Connects / Enables a specific Bluetooth device by name dynamically on any Windows PC.
    Works for any brand (Sony, Apple, Bose, Boat, OnePlus, Realme, JBL, Samsung, etc.).
    """
    if _OS != "Windows":
        return "Bluetooth device management is only supported on Windows in this build."

    target = _find_matching_device(device_name)
    if not target:
        all_devs = list_bluetooth_devices()
        dev_names = ", ".join([f"'{d['name']}'" for d in all_devs[:6]])
        return (
            f"Could not find Bluetooth device matching '{device_name}'. "
            f"Available devices on this system: {dev_names if dev_names else 'None found'}."
        )

    matched_name = target["name"]
    inst_id = target.get("instance_id", "")

    dev_match = re.search(r"DEV_([0-9A-F]{12})", inst_id, re.IGNORECASE)
    if dev_match:
        dev_filter = f"$_.InstanceId -match '{dev_match.group(1)}'"
    else:
        escaped_name = re.escape(matched_name)
        dev_filter = f"$_.FriendlyName -match '{escaped_name}' -or $_.InstanceId -eq '{inst_id}'"

    ps_connect = f"""
    $matched = Get-PnpDevice -Class Bluetooth -ErrorAction SilentlyContinue | Where-Object {{
        {dev_filter}
    }}
    foreach ($d in $matched) {{
        Enable-PnpDevice -InstanceId $d.InstanceId -Confirm:$false -ErrorAction SilentlyContinue
    }}
    """
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_connect],
            capture_output=True,
            text=True,
            timeout=8
        )
        print(f"[Bluetooth] Dynamic connect executed for: {matched_name}")
        return f"Bluetooth device '{matched_name}' connected successfully."
    except Exception as e:
        print(f"[Bluetooth] Error connecting device {matched_name}: {e}")
        return f"Failed to connect '{matched_name}': {e}"



def toggle_bluetooth_radio(state: str = "toggle") -> str:
    """
    Turns Windows Bluetooth radio ON, OFF, or toggles state.
    """
    if _OS != "Windows":
        return "Bluetooth radio control is only supported on Windows in this build."

    state = (state or "toggle").lower().strip()

    if state in ("off", "disable"):
        ps_cmd = """
        Get-PnpDevice -Class Bluetooth -ErrorAction SilentlyContinue | Where-Object {
            $_.FriendlyName -match "Radio" -or $_.InstanceId -match "USB\\\\VID_"
        } | ForEach-Object { Disable-PnpDevice -InstanceId $_.InstanceId -Confirm:$false -ErrorAction SilentlyContinue }
        """
        msg = "Bluetooth radio turned OFF."
    elif state in ("on", "enable"):
        ps_cmd = """
        Get-PnpDevice -Class Bluetooth -ErrorAction SilentlyContinue | Where-Object {
            $_.FriendlyName -match "Radio" -or $_.InstanceId -match "USB\\\\VID_"
        } | ForEach-Object { Enable-PnpDevice -InstanceId $_.InstanceId -Confirm:$false -ErrorAction SilentlyContinue }
        """
        msg = "Bluetooth radio turned ON."
    else:
        ps_cmd = """
        $radios = Get-PnpDevice -Class Bluetooth -ErrorAction SilentlyContinue | Where-Object {
            $_.FriendlyName -match "Radio" -or $_.InstanceId -match "USB\\\\VID_"
        }
        foreach ($r in $radios) {
            if ($r.Status -eq "OK") {
                Disable-PnpDevice -InstanceId $r.InstanceId -Confirm:$false -ErrorAction SilentlyContinue
            } else {
                Enable-PnpDevice -InstanceId $r.InstanceId -Confirm:$false -ErrorAction SilentlyContinue
            }
        }
        """
        msg = "Bluetooth radio toggled."

    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, text=True, timeout=6)
        return msg
    except Exception as e:
        return f"Error controlling Bluetooth radio: {e}"


def open_bluetooth_settings() -> str:
    """Opens Windows native Bluetooth settings page."""
    try:
        os.system("start ms-settings:bluetooth")
        return "Opened Windows Bluetooth settings."
    except Exception as e:
        return f"Error opening Bluetooth settings: {e}"


def bluetooth_control(action: Any = "list", device_name: str = "") -> str:
    """
    Master Bluetooth Dispatcher for INDUS.
    Supports both direct string actions and dictionary parameter payloads.
    """
    if isinstance(action, dict):
        device_name = action.get("device_name") or action.get("device", "") or device_name
        action = action.get("action", "list")

    act = (str(action) or "").lower().strip()

    if act in ("disconnect", "unpair", "remove", "disconnect_device"):
        if not device_name:
            return "Please specify the device name to disconnect (e.g. 'KH-Q8', 'realme Buds')."
        return disconnect_bluetooth_device(device_name)

    elif act in ("connect", "pair", "connect_device"):
        if not device_name:
            return "Please specify the device name to connect (e.g. 'KH-Q8', 'realme Buds')."
        return connect_bluetooth_device(device_name)

    elif act in ("list", "show", "status", "list_devices"):
        devs = list_bluetooth_devices()
        if not devs:
            return "No paired Bluetooth devices found."
        lines = ["Bluetooth Devices:"]
        for d in devs:
            lines.append(f"  * {d['name']} [{d['status']}]")
        return "\n".join(lines)

    elif act in ("turn_off", "off", "disable"):
        return toggle_bluetooth_radio("off")

    elif act in ("turn_on", "on", "enable"):
        return toggle_bluetooth_radio("on")

    elif act in ("toggle", "toggle_radio"):
        return toggle_bluetooth_radio("toggle")

    elif act in ("settings", "open_settings", "open"):
        return open_bluetooth_settings()

    else:
        if any(w in act for w in ["disconnect", "unpair", "off"]):
            return disconnect_bluetooth_device(device_name or act)
        elif any(w in act for w in ["connect", "pair"]):
            return connect_bluetooth_device(device_name or act)
        return open_bluetooth_settings()
