# core/security_engine.py
"""
INDUS Central Security Engine & Fail-Closed Policy Gate
======================================================
Evaluates every incoming tool call against 4-tier risk policies, enforce PIN
checks on DESTRUCTIVE actions, manages confirmation tokens, and guarantees
a strict FAIL-CLOSED invariant.
"""

from __future__ import annotations
import os
import sys
from typing import Dict, Any, Optional, Tuple

from core.audit_logger import audit_logger
from core.security_vault import is_pin_configured, verify_security_pin, is_locked_out
from core.confirmation_manager import confirmation_manager


# ── Risk Classifications ─────────────────────────────────────────────────────

DESTRUCTIVE_TOOLS_AND_ACTIONS = {
    "file_controller": ["delete", "remove", "wipe"],
    "computer_settings": ["shutdown", "restart", "power_off"],
    "security_protocols": ["panic", "emergency", "kill_switch"],
    "git_controller": ["reset_hard", "force_push", "clean_f"],
}

HIGH_RISK_TOOLS_AND_ACTIONS = {
    "terminal_command": None,
    "send_message": None,
    "mobile_bridge": ["sms", "call", "send_phone_sms", "make_phone_call"],
    "app_installer": None,
    "smart_downloader": None,
    "code_helper": ["run", "build", "execute"],
    "dev_agent": None,
    "security_vault": ["set", "clear"],
}

MEDIUM_RISK_TOOLS = {
    "file_processor", "file_controller", "computer_settings", "computer_control",
    "browser_control", "app_settings_navigator", "video_editor", "image_generator",
    "teleport_workspace", "game_updater", "smart_home", "bluetooth_control",
    "code_helper", "security_protocols", "git_controller", "proceed_to_cart_and_checkout",
    "live_writer", "mobile_bridge"
}

LOW_RISK_TOOLS = {
    "open_app", "web_search", "weather_report", "deep_research",
    "screen_understand", "screen_process", "vision_find_element",
    "vision_click", "vision_type", "vision_scroll", "vision_engine",
    "recall_memory", "search_conversation_history",
    "youtube_video", "system_radar", "flight_finder", "universal_ad_skipper",
    "save_memory", "save_media_source_preference", "search_and_show_products",
    "save_shopping_preference", "reminder", "stream_content"
}


class SecurityDecision:
    def __init__(
        self,
        allowed: bool,
        risk_level: str = "LOW",
        reason: str = "",
        requires_confirmation: bool = False,
        confirmation_token: str = "",
        target: str = ""
    ):
        self.allowed = allowed
        self.risk_level = risk_level.upper()
        self.reason = reason
        self.requires_confirmation = requires_confirmation
        self.confirmation_token = confirmation_token
        self.target = target

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed": self.allowed,
            "risk_level": self.risk_level,
            "reason": self.reason,
            "requires_confirmation": self.requires_confirmation,
            "confirmation_token": self.confirmation_token,
            "target": self.target,
        }


def extract_action_target(tool_name: str, parameters: dict) -> str:
    """Extracts target entity (file path, url, command, query) from parameters."""
    p = parameters or {}
    for key in ("file_path", "target", "path", "command", "query", "url", "receiver", "phone_number", "app_name"):
        val = p.get(key)
        if val:
            return str(val)
    return str(p.get("action", ""))


DESTRUCTIVE_LEGACY_ACTIONS = {
    "system_shutdown", "system_restart", "delete_file", "kill_process",
    "wipe_memory", "git_reset_hard", "git_push_force", "rmdir", "delete", "panic"
}

HIGH_LEGACY_ACTIONS = {
    "execute_terminal_command", "send_email", "send_sms", "make_call",
    "set_security_pin", "clear_security_pin", "send_phone_sms", "make_phone_call"
}


def classify_tool_risk(tool_name: str, parameters: dict = None) -> str:
    """
    Determines risk level: DESTRUCTIVE, HIGH, MEDIUM, LOW, or UNKNOWN.
    """
    tool = str(tool_name).lower().strip()
    params = parameters or {}
    sub_action = str(params.get("action", "")).lower().strip()

    # 0. Check Direct Action Strings (Legacy / helper compatibility)
    if tool in DESTRUCTIVE_LEGACY_ACTIONS or any(d in tool for d in ("shutdown", "delete_file", "kill_process", "wipe_memory")):
        return "DESTRUCTIVE"
    if tool in HIGH_LEGACY_ACTIONS or any(h in tool for h in ("terminal_command", "execute_terminal", "send_sms", "make_call")):
        return "HIGH"

    # 1. Check Destructive Tools
    if tool in DESTRUCTIVE_TOOLS_AND_ACTIONS:
        blocked_actions = DESTRUCTIVE_TOOLS_AND_ACTIONS[tool]
        if blocked_actions is None or sub_action in blocked_actions or any(b in sub_action for b in blocked_actions):
            return "DESTRUCTIVE"

    # Check parameter text for destructive keywords
    for v in params.values():
        if isinstance(v, str):
            v_lower = v.lower()
            if any(k in v_lower for k in ("format c:", "rmdir /s /q", "del /f /s /q c:\\", "shutdown -s")):
                return "DESTRUCTIVE"

    # 2. Check High Risk Tools
    if tool in HIGH_RISK_TOOLS_AND_ACTIONS:
        high_actions = HIGH_RISK_TOOLS_AND_ACTIONS[tool]
        if high_actions is None or not high_actions or sub_action in high_actions:
            return "HIGH"

    # 3. Check Medium Risk Tools
    if tool in MEDIUM_RISK_TOOLS:
        return "MEDIUM"

    # 4. Check Low Risk Tools
    if tool in LOW_RISK_TOOLS:
        return "LOW"

    # Tool is unregistered / unknown
    return "UNKNOWN"


def evaluate_tool_execution(
    tool_name: str,
    parameters: dict = None,
    user_context: dict = None
) -> SecurityDecision:
    """
    Central Fail-Closed Policy Gatekeeper.
    Evaluates tool invocation against risk matrix, PIN verification, and confirmation tokens.
    Guarantees FAIL-CLOSED on any error.
    """
    try:
        tool = str(tool_name).lower().strip()
        params = parameters or {}
        target = extract_action_target(tool, params)
        risk = classify_tool_risk(tool, params)

        # UNKNOWN Tool Policy -> Replan directive
        if risk == "UNKNOWN":
            audit_logger.log_event(
                event_type="SECURITY_DECISION",
                tool=tool,
                target=target,
                risk_level="UNKNOWN",
                decision="DENY",
                reason=f"Unknown tool '{tool}'. Blocked by Fail-Closed policy."
            )
            return SecurityDecision(
                allowed=False,
                risk_level="UNKNOWN",
                reason=f"Tool '{tool}' is unrecognized. Action blocked.",
                target=target
            )

        # LOW Risk Policy -> Auto-allowed
        if risk == "LOW":
            audit_logger.log_event(
                event_type="SECURITY_DECISION",
                tool=tool,
                target=target,
                risk_level="LOW",
                decision="ALLOW",
                reason="Permitted under LOW risk policy"
            )
            return SecurityDecision(allowed=True, risk_level="LOW", reason="Permitted", target=target)

        # MEDIUM Risk Policy -> Auto-allowed in interactive session
        if risk == "MEDIUM":
            audit_logger.log_event(
                event_type="SECURITY_DECISION",
                tool=tool,
                target=target,
                risk_level="MEDIUM",
                decision="ALLOW",
                reason="Permitted under MEDIUM risk policy"
            )
            return SecurityDecision(allowed=True, risk_level="MEDIUM", reason="Permitted", target=target)

        # Check for pre-supplied confirmation token or explicit user confirmation
        confirm_token = str(params.get("confirmation_token", "")).strip()
        confirmed_flag = str(params.get("confirmed", "")).lower() in ("yes", "true", "1", "confirm")

        if confirm_token:
            is_valid, v_msg = confirmation_manager.validate_and_consume(confirm_token, tool, target)
            if is_valid:
                audit_logger.log_event(
                    event_type="SECURITY_DECISION",
                    tool=tool,
                    target=target,
                    risk_level=risk,
                    decision="ALLOW",
                    reason="Permitted via valid confirmation token"
                )
                return SecurityDecision(allowed=True, risk_level=risk, reason="Confirmed by token", target=target)
            else:
                audit_logger.log_event(
                    event_type="SECURITY_DECISION",
                    tool=tool,
                    target=target,
                    risk_level=risk,
                    decision="DENY",
                    reason=f"Confirmation token rejected: {v_msg}"
                )
                return SecurityDecision(
                    allowed=False,
                    risk_level=risk,
                    reason=f"Confirmation invalid: {v_msg}",
                    target=target
                )

        # DESTRUCTIVE Risk Policy -> Enforce PIN or explicit confirmation
        if risk == "DESTRUCTIVE":
            if is_pin_configured():
                supplied_pin = str(params.get("pin", "")).strip()
                if not supplied_pin:
                    req = confirmation_manager.create_confirmation_request(tool, target, "DESTRUCTIVE")
                    return SecurityDecision(
                        allowed=False,
                        risk_level="DESTRUCTIVE",
                        reason="Destructive action blocked: Security PIN or explicit confirmation required.",
                        requires_confirmation=True,
                        confirmation_token=req.token,
                        target=target
                    )
                if not verify_security_pin(supplied_pin):
                    return SecurityDecision(
                        allowed=False,
                        risk_level="DESTRUCTIVE",
                        reason="Destructive action blocked: Invalid PIN or vault lockout.",
                        target=target
                    )

            if not confirmed_flag:
                req = confirmation_manager.create_confirmation_request(tool, target, "DESTRUCTIVE")
                return SecurityDecision(
                    allowed=False,
                    risk_level="DESTRUCTIVE",
                    reason=f"This will execute a DESTRUCTIVE action on '{target}'. Confirmation required.",
                    requires_confirmation=True,
                    confirmation_token=req.token,
                    target=target
                )

            audit_logger.log_event(
                event_type="SECURITY_DECISION",
                tool=tool,
                target=target,
                risk_level="DESTRUCTIVE",
                decision="ALLOW",
                reason="Permitted under confirmed DESTRUCTIVE policy"
            )
            return SecurityDecision(allowed=True, risk_level="DESTRUCTIVE", reason="Confirmed", target=target)

        # HIGH Risk Policy
        if risk == "HIGH":
            # If confirmed via parameter flag or auto-allowed in direct chat
            if confirmed_flag:
                return SecurityDecision(allowed=True, risk_level="HIGH", reason="Confirmed by user", target=target)

            # Auto-allow developer CLI tools when user explicitly typed command, but audit log
            audit_logger.log_event(
                event_type="SECURITY_DECISION",
                tool=tool,
                target=target,
                risk_level="HIGH",
                decision="ALLOW",
                reason="Auto-permitted high-risk tool under active user session"
            )
            return SecurityDecision(allowed=True, risk_level="HIGH", reason="Permitted", target=target)

        return SecurityDecision(allowed=True, risk_level="LOW", reason="Permitted", target=target)

    except Exception as e:
        # ── FAIL-CLOSED INVARIANT ────────────────────────────────────────────
        audit_logger.log_security_alert(
            alert_type="FAIL_CLOSED_EXCEPTION",
            tool=tool_name,
            details=f"Security gate exception: {e}",
            severity="DESTRUCTIVE"
        )
        return SecurityDecision(
            allowed=False,
            risk_level="DESTRUCTIVE",
            reason=f"Security policy evaluation error: {e} (Action blocked by Fail-Closed invariant).",
            target=""
        )


# Global singleton export
security_engine = evaluate_tool_execution
