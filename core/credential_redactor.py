# core/credential_redactor.py
"""
INDUS Sensitive Data & Credential Redaction Engine
=================================================
Ensures API keys, tokens, passwords, and private credentials never leak into
logs, HUD event streams, audit records, or UI error outputs.
"""

from __future__ import annotations
import re
from typing import Any, Dict, List, Union

REDACTED_STR = "***REDACTED***"

# Compiled regex patterns for well-known API keys and sensitive tokens
_PATTERNS = [
    # Google Gemini / Cloud API keys: AIzaSy...
    re.compile(r"AIza[0-9A-Za-z_\-]{16,50}"),
    # OpenAI / OpenRouter API keys: sk-...
    re.compile(r"sk-[a-zA-Z0-9_\-]{20,}"),
    # Anthropic API keys: sk-ant-...
    re.compile(r"sk-ant-[a-zA-Z0-9_\-]{20,}"),
    # Groq API keys: gsk_...
    re.compile(r"gsk_[a-zA-Z0-9_\-]{20,}"),
    # NVIDIA API keys: nvapi-...
    re.compile(r"nvapi-[a-zA-Z0-9_\-]{20,}"),
    # HTTP Authorization Bearer tokens
    re.compile(r"Bearer\s+[A-Za-z0-9\-\._~\+\/]+=*", re.IGNORECASE),
    # Key-value secret patterns in JSON/logs (e.g. "api_key": "xxx", "password": "xxx")
    re.compile(
        r"""(?i)(["']?(?:api[_-]?key|password|passwd|secret|pin|auth_token|private_key|token)["']?\s*[:=]\s*["'])([^"'\s]{4,})(["'])"""
    ),
]

_SENSITIVE_FIELD_NAMES = {
    "api_key", "gemini_api_key", "openrouter_api_key", "groq_api_key",
    "nvidia_api_key", "tavily_api_key", "password", "pin", "secret",
    "token", "auth_token", "private_key", "credential"
}


def redact_sensitive(text: Union[str, Any]) -> str:
    """
    Scans any string or object for API keys, authorization tokens, and credentials,
    replacing them with '***REDACTED***'.
    """
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)

    cleaned = text
    for pat in _PATTERNS:
        if pat.groups > 0:
            # For regex with capture groups (key-value replacement)
            cleaned = pat.sub(r"\g<1>" + REDACTED_STR + r"\g<3>", cleaned)
        else:
            cleaned = pat.sub(REDACTED_STR, cleaned)
    return cleaned


def redact_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively scans and redacts sensitive keys and values in a dictionary.
    """
    if not isinstance(data, dict):
        return data

    redacted = {}
    for k, v in data.items():
        k_lower = str(k).lower()
        if any(sens in k_lower for sens in _SENSITIVE_FIELD_NAMES):
            redacted[k] = REDACTED_STR
        elif isinstance(v, dict):
            redacted[k] = redact_dict(v)
        elif isinstance(v, list):
            redacted[k] = [
                redact_dict(item) if isinstance(item, dict)
                else redact_sensitive(item) if isinstance(item, str)
                else item
                for item in v
            ]
        elif isinstance(v, str):
            redacted[k] = redact_sensitive(v)
        else:
            redacted[k] = v
    return redacted
