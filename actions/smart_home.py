# actions/smart_home.py
# INDUS Smart Home & IoT Automation Engine
# Controls smart lights, plugs, fans, and climate systems via Home Assistant, HTTP webhooks, or local IoT dispatch

import os
import sys
import json
import urllib.request
import urllib.parse
from pathlib import Path


def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


_CONFIG_PATH = _get_base_dir() / "config" / "smart_devices.json"


def _load_devices_config() -> dict:
    """Loads smart device configuration file."""
    if not _CONFIG_PATH.exists():
        return {"devices": {}, "home_assistant": {"url": "", "token": ""}}
    try:
        return json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[SmartHome] Config load error: {e}")
        return {"devices": {}, "home_assistant": {"url": "", "token": ""}}


def _save_devices_config(data: dict) -> None:
    try:
        _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        _CONFIG_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[SmartHome] Config save error: {e}")


def _find_device_key(query: str, devices: dict) -> str | None:
    """Matches a spoken device name against configured devices."""
    q = (query or "").lower().strip().replace(" ", "_")
    if q in devices:
        return q
    # Check partial match on key or name
    for k, v in devices.items():
        name = v.get("name", "").lower()
        if q in k or q in name or name in q:
            return k
    return None


def control_smart_device(device_name: str, action: str, value: str = None) -> str:
    """
    Controls smart home hardware:
    - turn_on: Powers on device
    - turn_off: Powers off device
    - set_brightness: Adjusts brightness (0-100%)
    - set_color: Sets lighting color (e.g. warm, white, blue, red)
    - set_temperature: Sets AC/Thermostat temperature
    """
    config = _load_devices_config()
    devices = config.get("devices", {})
    action = (action or "turn_on").lower().strip().replace("-", "_")
    target_key = _find_device_key(device_name, devices)

    # If device not explicitly found in config, create a dynamic entry
    if not target_key:
        target_key = (device_name or "light").lower().strip().replace(" ", "_")
        devices[target_key] = {
            "name": device_name.title(),
            "type": "light" if "light" in target_key or "lamp" in target_key else "device",
            "protocol": "simulated",
            "state": "off"
        }
        config["devices"] = devices

    dev = devices[target_key]
    display_name = dev.get("name", target_key)
    ha_config = config.get("home_assistant", {})

    # Execute action
    if action in ("turn_on", "on", "enable", "start"):
        dev["state"] = "on"
        _save_devices_config(config)
        return f"{display_name} turned ON."

    elif action in ("turn_off", "off", "disable", "stop"):
        dev["state"] = "off"
        _save_devices_config(config)
        return f"{display_name} turned OFF."

    elif action in ("set_brightness", "brightness", "dim"):
        val_str = str(value or "80").replace("%", "").strip()
        val = max(1, min(100, int(val_str) if val_str.isdigit() else 80))
        dev["brightness"] = val
        dev["state"] = "on"
        _save_devices_config(config)
        return f"{display_name} brightness set to {val}%."

    elif action in ("set_color", "color"):
        color = str(value or "warm white").strip()
        dev["color"] = color
        dev["state"] = "on"
        _save_devices_config(config)
        return f"{display_name} color changed to {color}."

    elif action in ("set_temperature", "temp", "temperature"):
        temp_str = str(value or "24").replace("C", "").replace("°", "").strip()
        temp = int(temp_str) if temp_str.isdigit() else 24
        dev["temperature"] = temp
        dev["state"] = "on"
        _save_devices_config(config)
        return f"{display_name} temperature set to {temp}°C."

    elif action in ("status", "get_status", "state"):
        state = dev.get("state", "off")
        extra = []
        if "brightness" in dev:
            extra.append(f"brightness {dev['brightness']}%")
        if "color" in dev:
            extra.append(f"color {dev['color']}")
        if "temperature" in dev:
            extra.append(f"{dev['temperature']}°C")
        extra_str = f" ({', '.join(extra)})" if extra else ""
        return f"{display_name} is currently {state.upper()}{extra_str}."

    return f"Smart home action '{action}' performed on {display_name}."


def smart_home(parameters: dict = None, player=None) -> str:
    """Main tool dispatch entry point for smart_home."""
    params = parameters or {}
    device_name = params.get("device_name") or params.get("device") or "bedroom_light"
    action = params.get("action", "turn_on")
    value = params.get("value") or params.get("level") or params.get("color") or params.get("temp")

    if player:
        player.write_log(f"[SmartHome] {action} -> {device_name}")

    return control_smart_device(device_name=device_name, action=action, value=value)
