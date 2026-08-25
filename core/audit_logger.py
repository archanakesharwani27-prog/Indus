# core/audit_logger.py
"""
INDUS Structured Security Audit Logger
======================================
Maintains an immutable, append-only audit trail of all security-sensitive
evaluations, permissions, code executions, PIN authentications, and policy decisions.
All entries are automatically sanitized through credential_redactor.
"""

from __future__ import annotations
import os
import sys
import json
import time
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from core.credential_redactor import redact_dict, redact_sensitive


def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = _get_base_dir()
AUDIT_LOG_FILE = BASE_DIR / "logs" / "security_audit.jsonl"


class SecurityAuditLogger:
    """Thread-safe append-only structured audit logger for INDUS security events."""

    def __init__(self, log_path: Optional[Path] = None):
        self.log_path = log_path or AUDIT_LOG_FILE
        self._lock = threading.Lock()
        self._ensure_dir()

    def _ensure_dir(self):
        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    def log_event(
        self,
        event_type: str,
        tool: str = "",
        target: str = "",
        risk_level: str = "LOW",
        decision: str = "ALLOW",
        reason: str = "",
        user_command: str = "",
        execution_status: str = "PENDING",
        verification_status: str = "UNVERIFIED",
        extra_metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Appends a structured, sanitized security record to the audit log.
        Returns the generated event ID.
        """
        event_id = str(uuid.uuid4())
        record = {
            "event_id": event_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "tool": tool,
            "target": redact_sensitive(target),
            "risk_level": risk_level.upper(),
            "decision": decision.upper(),
            "reason": reason,
            "user_command": redact_sensitive(user_command),
            "execution_status": execution_status.upper(),
            "verification_status": verification_status.upper(),
            "metadata": extra_metadata or {},
        }

        sanitized = redact_dict(record)

        try:
            with self._lock:
                self._ensure_dir()
                with open(self.log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(sanitized) + "\n")
        except Exception as e:
            print(f"[AuditLogger] Write error: {e}")

        return event_id

    def log_security_alert(self, alert_type: str, tool: str, details: str, severity: str = "HIGH"):
        """Convenience method for security warnings, exceptions, or unauthorized attempts."""
        return self.log_event(
            event_type="SECURITY_ALERT",
            tool=tool,
            risk_level=severity,
            decision="DENY",
            reason=details,
            execution_status="BLOCKED"
        )


# Global singleton instance
audit_logger = SecurityAuditLogger()
