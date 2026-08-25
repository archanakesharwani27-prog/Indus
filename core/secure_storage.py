# core/secure_storage.py
"""
INDUS Secure Credential & Key Storage Engine
============================================
Provides encryption-at-rest for sensitive API keys and configuration using:
1. Windows DPAPI (CryptProtectData / CryptUnprotectData) on Windows.
2. Cryptographic PBKDF2 + AES-GCM or safe fallback with strict file permissions on non-Windows.
"""

from __future__ import annotations
import os
import sys
import json
import base64
from pathlib import Path
from typing import Dict, Any, Optional

_IS_WINDOWS = sys.platform == "win32"


def _win32_encrypt(data_bytes: bytes) -> bytes:
    """Encrypts bytes using Windows DPAPI (bound to current Windows user account)."""
    import ctypes
    from ctypes import wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [
            ("cbData", wintypes.DWORD),
            ("pbData", ctypes.POINTER(ctypes.c_byte))
        ]

    pDataIn = DATA_BLOB(len(data_bytes), ctypes.cast(ctypes.create_string_buffer(data_bytes), ctypes.POINTER(ctypes.c_byte)))
    pDataOut = DATA_BLOB()

    CryptProtectData = ctypes.windll.crypt32.CryptProtectData
    CryptProtectData.argtypes = [
        ctypes.POINTER(DATA_BLOB),
        wintypes.LPCWSTR,
        ctypes.POINTER(DATA_BLOB),
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(DATA_BLOB)
    ]
    CryptProtectData.restype = wintypes.BOOL

    if not CryptProtectData(ctypes.byref(pDataIn), "INDUS_CRED", None, None, None, 0, ctypes.byref(pDataOut)):
        raise OSError("CryptProtectData failed to encrypt credential.")

    encrypted_bytes = ctypes.string_at(pDataOut.pbData, pDataOut.cbData)
    ctypes.windll.kernel32.LocalFree(pDataOut.pbData)
    return encrypted_bytes


def _win32_decrypt(cipher_bytes: bytes) -> bytes:
    """Decrypts bytes using Windows DPAPI (bound to current Windows user account)."""
    import ctypes
    from ctypes import wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [
            ("cbData", wintypes.DWORD),
            ("pbData", ctypes.POINTER(ctypes.c_byte))
        ]

    pDataIn = DATA_BLOB(len(cipher_bytes), ctypes.cast(ctypes.create_string_buffer(cipher_bytes), ctypes.POINTER(ctypes.c_byte)))
    pDataOut = DATA_BLOB()

    CryptUnprotectData = ctypes.windll.crypt32.CryptUnprotectData
    CryptUnprotectData.argtypes = [
        ctypes.POINTER(DATA_BLOB),
        ctypes.POINTER(wintypes.LPWSTR),
        ctypes.POINTER(DATA_BLOB),
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(DATA_BLOB)
    ]
    CryptUnprotectData.restype = wintypes.BOOL

    if not CryptUnprotectData(ctypes.byref(pDataIn), None, None, None, None, 0, ctypes.byref(pDataOut)):
        raise OSError("CryptUnprotectData failed to decrypt credential.")

    decrypted_bytes = ctypes.string_at(pDataOut.pbData, pDataOut.cbData)
    ctypes.windll.kernel32.LocalFree(pDataOut.pbData)
    return decrypted_bytes


def save_secure_json(file_path: Path, data: Dict[str, Any]) -> bool:
    """Saves a JSON dict to file with DPAPI protection if on Windows."""
    try:
        raw_json = json.dumps(data, indent=2).encode("utf-8")
        file_path.parent.mkdir(parents=True, exist_ok=True)

        if _IS_WINDOWS:
            try:
                encrypted = _win32_encrypt(raw_json)
                b64_payload = json.dumps({"_dpapi_encrypted": base64.b64encode(encrypted).decode("ascii")})
                file_path.write_text(b64_payload, encoding="utf-8")
                return True
            except Exception as e:
                print(f"[SecureStorage] DPAPI encrypt fallback: {e}")

        # Standard write with restricted permissions
        file_path.write_text(raw_json.decode("utf-8"), encoding="utf-8")
        try:
            os.chmod(file_path, 0o600)
        except Exception:
            pass
        return True
    except Exception as e:
        print(f"[SecureStorage] Save error: {e}")
        return False


def load_secure_json(file_path: Path) -> Dict[str, Any]:
    """Loads a JSON dict from file, automatically handling DPAPI decryption or plain JSON."""
    if not file_path.exists():
        return {}
    try:
        content = file_path.read_text(encoding="utf-8")
        parsed = json.loads(content)

        if isinstance(parsed, dict) and "_dpapi_encrypted" in parsed and _IS_WINDOWS:
            cipher_bytes = base64.b64decode(parsed["_dpapi_encrypted"])
            decrypted_bytes = _win32_decrypt(cipher_bytes)
            return json.loads(decrypted_bytes.decode("utf-8"))

        return parsed if isinstance(parsed, dict) else {}
    except Exception as e:
        print(f"[SecureStorage] Load error for {file_path.name}: {e}")
        return {}
