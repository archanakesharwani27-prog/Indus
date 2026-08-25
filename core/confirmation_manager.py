# core/confirmation_manager.py
"""
INDUS Action-Target Bound Confirmation Manager
==============================================
Issues and validates cryptographically bound, single-use confirmation tokens.
Enforces that user approvals are bound to EXACT actions and EXACT targets with
a 60-second time-to-live.
"""

from __future__ import annotations
import os
import time
import hmac
import hashlib
import threading
from typing import Dict, Optional, Tuple

from core.audit_logger import audit_logger


CONFIRMATION_TTL_SECONDS = 60.0


class ConfirmationRecord:
    def __init__(self, action: str, target: str, risk_level: str, token: str):
        self.action = action.lower().strip()
        self.target = str(target or "").strip()
        self.risk_level = risk_level.upper()
        self.token = token
        self.created_at = time.time()
        self.expires_at = self.created_at + CONFIRMATION_TTL_SECONDS
        self.used = False

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at


class ActionConfirmationManager:
    """Manages secure, parameter-tamper-proof action confirmation tokens."""

    def __init__(self):
        self._secret = os.urandom(32)
        self._lock = threading.Lock()
        self._pending: Dict[str, ConfirmationRecord] = {}

    def _generate_token(self, action: str, target: str) -> str:
        nonce = os.urandom(8).hex()
        msg = f"{action}:{target}:{nonce}:{time.time()}".encode("utf-8")
        return hmac.new(self._secret, msg, hashlib.sha256).hexdigest()[:24]

    def create_confirmation_request(
        self, action: str, target: str, risk_level: str = "HIGH"
    ) -> ConfirmationRecord:
        """Creates and tracks a new bound confirmation request."""
        clean_action = str(action).lower().strip()
        clean_target = str(target or "").strip()
        token = self._generate_token(clean_action, clean_target)

        record = ConfirmationRecord(
            action=clean_action,
            target=clean_target,
            risk_level=risk_level,
            token=token
        )

        with self._lock:
            # Clean expired records
            now = time.time()
            self._pending = {k: v for k, v in self._pending.items() if v.expires_at > now}
            self._pending[token] = record

        audit_logger.log_event(
            event_type="CONFIRMATION_REQUEST",
            tool=clean_action,
            target=clean_target,
            risk_level=risk_level,
            decision="CONFIRM_REQUIRED",
            reason=f"Action requires explicit approval for target: '{clean_target}'"
        )

        return record

    def validate_and_consume(
        self, token: str, current_action: str, current_target: str
    ) -> Tuple[bool, str]:
        """
        Validates token and ensures action and target have not been modified or tampered with.
        Consumes the token on successful verification (single-use).
        """
        clean_action = str(current_action).lower().strip()
        clean_target = str(current_target or "").strip()

        with self._lock:
            record = self._pending.get(token)
            if not record:
                return False, "Invalid or expired confirmation token."

            if record.used:
                return False, "Confirmation token has already been used."

            if record.is_expired:
                del self._pending[token]
                return False, "Confirmation token has expired (60s limit exceeded)."

            # Strict Action & Target Bound Match
            if record.action != clean_action:
                return False, f"Action mismatch: Token was issued for '{record.action}', got '{clean_action}'."

            if record.target != clean_target:
                return False, f"Target mismatch: Token was issued for target '{record.target}', got '{clean_target}'."

            # Mark consumed
            record.used = True
            del self._pending[token]

        audit_logger.log_event(
            event_type="CONFIRMATION_RESPONSE",
            tool=clean_action,
            target=clean_target,
            risk_level=record.risk_level,
            decision="CONFIRMED",
            reason="User confirmation token successfully verified"
        )

        return True, "Confirmation verified."

    def cancel_confirmation(self, token: str) -> bool:
        """Cancels a pending confirmation."""
        with self._lock:
            record = self._pending.pop(token, None)
            if record:
                audit_logger.log_event(
                    event_type="CONFIRMATION_RESPONSE",
                    tool=record.action,
                    target=record.target,
                    risk_level=record.risk_level,
                    decision="CANCELLED",
                    reason="User cancelled confirmation request"
                )
                return True
        return False


# Global singleton instance
confirmation_manager = ActionConfirmationManager()
