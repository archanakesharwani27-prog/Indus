# core/security_vault.py
"""
INDUS Cryptographic Security Vault & Authentication Engine
==========================================================
Provides PBKDF2-HMAC-SHA256 salted PIN authentication, constant-time verification,
consecutive failed attempt rate-limiting/lockouts, and risk-tier classification.
"""

from __future__ import annotations
import os
import sys
import json
import time
import hmac
import hashlib
import threading
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

from core.audit_logger import audit_logger


def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = _get_base_dir()
_PIN_FILE = BASE_DIR / "config" / "security_pin.json"

# PBKDF2 parameters
_PBKDF2_ITERATIONS = 100_000
_SALT_BYTES = 16

# Rate limiting / Lockout parameters
_MAX_FAILED_ATTEMPTS = 3
_LOCKOUT_DURATION_SEC = 60.0

_vault_lock = threading.Lock()
_failed_attempts = 0
_lockout_until = 0.0


def _derive_hash(pin: str, salt_bytes: bytes) -> bytes:
    """Derive cryptographic key from PIN using PBKDF2-HMAC-SHA256."""
    return hashlib.pbkdf2_hmac(
        "sha256",
        pin.encode("utf-8"),
        salt_bytes,
        _PBKDF2_ITERATIONS
    )


def _load_pin_record() -> Tuple[Optional[bytes], Optional[bytes]]:
    """Loads salt and hash bytes from security_pin.json."""
    try:
        if not _PIN_FILE.exists():
            return None, None
        with open(_PIN_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Support backward compatibility if plain PIN existed previously
        if "salt_hex" in data and "hash_hex" in data:
            return bytes.fromhex(data["salt_hex"]), bytes.fromhex(data["hash_hex"])
        elif "pin" in data:
            # Upgrade legacy plaintext pin on the fly
            legacy_pin = str(data["pin"]).strip()
            if legacy_pin:
                salt = os.urandom(_SALT_BYTES)
                derived = _derive_hash(legacy_pin, salt)
                _save_pin_record(salt, derived)
                return salt, derived
    except Exception as e:
        print(f"[SecurityVault] Failed to load PIN record: {e}")
    return None, None


def _save_pin_record(salt_bytes: bytes, hash_bytes: bytes) -> bool:
    """Saves salt and hash bytes in hex format."""
    try:
        _PIN_FILE.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "salt_hex": salt_bytes.hex(),
            "hash_hex": hash_bytes.hex(),
            "iterations": _PBKDF2_ITERATIONS,
            "algorithm": "PBKDF2-HMAC-SHA256",
        }
        with open(_PIN_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        return True
    except Exception as e:
        print(f"[SecurityVault] Failed to save PIN record: {e}")
        return False


def is_pin_configured() -> bool:
    """Check if a security PIN is currently active."""
    salt, hash_val = _load_pin_record()
    return salt is not None and hash_val is not None


def is_locked_out() -> Tuple[bool, float]:
    """Returns (is_locked, remaining_seconds)."""
    global _lockout_until
    with _vault_lock:
        now = time.time()
        if now < _lockout_until:
            return True, round(_lockout_until - now, 1)
        return False, 0.0


def verify_security_pin(pin: str, player=None) -> bool:
    """
    Verifies supplied PIN against stored PBKDF2 hash using constant-time comparison.
    Enforces lockout if consecutive failed attempts exceed threshold.
    """
    global _failed_attempts, _lockout_until

    salt, stored_hash = _load_pin_record()
    if salt is None or stored_hash is None:
        # No PIN set; default allow
        return True

    now = time.time()
    with _vault_lock:
        if now < _lockout_until:
            rem = int(_lockout_until - now)
            msg = f"Security Vault is locked out. Try again in {rem}s."
            if player:
                player.write_log(f"[Vault] {msg}")
            audit_logger.log_event(
                event_type="PIN_AUTH",
                tool="security_vault",
                decision="DENY",
                reason=f"Account locked out. Remaining: {rem}s"
            )
            return False

        supplied_pin = str(pin or "").strip()
        computed_hash = _derive_hash(supplied_pin, salt)

        # Constant-time comparison prevents timing side-channel attacks
        is_valid = hmac.compare_digest(computed_hash, stored_hash)

        if is_valid:
            _failed_attempts = 0
            _lockout_until = 0.0
            if player:
                player.write_log("[Vault] PIN verified successfully.")
            audit_logger.log_event(
                event_type="PIN_AUTH",
                tool="security_vault",
                decision="ALLOW",
                reason="PIN verified successfully"
            )
            return True
        else:
            _failed_attempts += 1
            if _failed_attempts >= _MAX_FAILED_ATTEMPTS:
                _lockout_until = now + _LOCKOUT_DURATION_SEC
                _failed_attempts = 0
                msg = f"Too many failed PIN attempts. Locked out for {_LOCKOUT_DURATION_SEC}s."
            else:
                remaining_tries = _MAX_FAILED_ATTEMPTS - _failed_attempts
                msg = f"Wrong PIN. {remaining_tries} attempt(s) remaining."

            if player:
                player.write_log(f"[Vault] {msg}")
            audit_logger.log_event(
                event_type="PIN_AUTH",
                tool="security_vault",
                decision="DENY",
                reason=msg
            )
            return False


def set_security_pin(new_pin: str, player=None) -> str:
    """Sets a new 4 to 6 digit security PIN with fresh salt."""
    pin_str = str(new_pin or "").strip()
    if not pin_str.isdigit() or len(pin_str) not in (4, 5, 6):
        return "PIN must be between 4 and 6 numeric digits."

    salt = os.urandom(_SALT_BYTES)
    derived = _derive_hash(pin_str, salt)

    if _save_pin_record(salt, derived):
        if player:
            player.write_log("[Vault] New salted Security PIN configured.")
        audit_logger.log_event(
            event_type="PIN_AUTH",
            tool="security_vault",
            decision="ALLOW",
            reason="New security PIN created with PBKDF2-HMAC-SHA256"
        )
        return "Security PIN successfully set ho gaya."
    return "Failed to save Security PIN."


def clear_security_pin(player=None) -> str:
    """Clears the stored security PIN."""
    try:
        if _PIN_FILE.exists():
            _PIN_FILE.unlink()
        if player:
            player.write_log("[Vault] Security PIN removed.")
        audit_logger.log_event(
            event_type="PIN_AUTH",
            tool="security_vault",
            decision="ALLOW",
            reason="Security PIN deleted"
        )
        return "Security PIN remove ho gaya."
    except Exception as e:
        return f"Failed to clear PIN: {e}"


def security_vault(parameters: dict, player=None) -> str:
    """Tool entry point for security_vault."""
    params = parameters or {}
    action = str(params.get("action", "verify")).lower().strip()

    if action in ("verify", "check"):
        pin = str(params.get("pin", ""))
        ok = verify_security_pin(pin, player)
        return "Access granted." if ok else "Wrong PIN or locked out. Access denied."

    elif action in ("set", "create"):
        return set_security_pin(params.get("pin", ""), player)

    elif action in ("clear", "remove", "delete"):
        return clear_security_pin(player)

    return f"Unknown vault action: {action}"


# Backward compatibility aliases for existing codebase & tests
RISK_LEVELS = {
    "DESTRUCTIVE": [
        "delete_file", "kill_process", "system_shutdown", "system_restart",
        "wipe_memory", "git_reset_hard", "git_push_force", "rmdir", "delete"
    ],
    "HIGH": [
        "execute_terminal_command", "send_email", "send_sms", "make_call",
        "set_security_pin", "clear_security_pin", "send_phone_sms", "make_phone_call"
    ],
    "MEDIUM": [
        "modify_file", "set_brightness", "set_volume", "teleport_workspace",
        "mouse_click", "keyboard_press", "browser_fill", "browser_click"
    ],
    "LOW": [
        "screen_understand", "ocr", "ground_ui_element", "search_web",
        "deep_research", "weather_report", "remember", "get_preference",
        "open_app", "youtube_video", "desktop_actions"
    ],
}


def classify_action_risk(action_name: str, parameters: dict = None) -> str:
    from core.security_engine import classify_tool_risk
    return classify_tool_risk(action_name, parameters)


def evaluate_action(action_name: str, parameters: dict = None):
    from core.security_engine import evaluate_tool_execution
    return evaluate_tool_execution(action_name, parameters)


security_vault.evaluate_action = evaluate_action
security_vault.classify_action_risk = classify_action_risk
security_vault.RISK_LEVELS = RISK_LEVELS
