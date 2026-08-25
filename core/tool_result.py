# core/tool_result.py
"""
INDUS Standard Tool Result Contract.

Every action module ultimately returns or can be adapted to a ToolResult.
The dispatcher in main.py._execute_tool uses normalize_result() to convert
raw string/dict returns from legacy tool functions into ToolResult, so the
33 action modules do NOT need to be rewritten all at once.

Usage — new tools:
    return ToolResult(success=True, message="Chrome opened.", data={"pid": 1234})

Usage — dispatcher adapter:
    raw = some_legacy_tool(parameters=args)
    result = normalize_result(raw, tool_name="open_app")

Usage — callers reading result:
    if result.success:
        speak(result.message)
    else:
        error_handler.classify(result.error)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class ToolResult:
    """
    Unified result contract for every INDUS tool.

    Fields
    ------
    success   : bool         — True if the tool completed its intended action
    message   : str          — Human-readable summary (used in TTS / UI log)
    data      : dict         — Structured payload (e.g. coordinates, pid, url)
    error     : Optional[str]— Machine-readable error code / exception text
    cancelled : bool         — True if the tool was interrupted by CancellationManager
    verified  : bool         — True if ActionVerifier confirmed the real-world outcome
    """

    success: bool
    message: str
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    cancelled: bool = False
    verified: bool = False

    # ------------------------------------------------------------------ #
    #  Conversion helpers                                                   #
    # ------------------------------------------------------------------ #

    def to_str(self) -> str:
        """
        Return a human-readable string — identical to what legacy callers
        (main.py, agent_loop, TTS) already expect.
        """
        return self.message

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "message": self.message,
            "data": self.data,
            "error": self.error,
            "cancelled": self.cancelled,
            "verified": self.verified,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ToolResult":
        return cls(
            success=d.get("success", False),
            message=d.get("message", ""),
            data=d.get("data", {}),
            error=d.get("error"),
            cancelled=d.get("cancelled", False),
            verified=d.get("verified", False),
        )

    # ------------------------------------------------------------------ #
    #  Factory helpers                                                      #
    # ------------------------------------------------------------------ #

    @classmethod
    def ok(cls, message: str, data: dict = None, verified: bool = False) -> "ToolResult":
        """Convenience factory for a successful result."""
        return cls(success=True, message=message, data=data or {}, verified=verified)

    @classmethod
    def fail(cls, message: str, error: str = "", data: dict = None) -> "ToolResult":
        """Convenience factory for a failed result."""
        return cls(success=False, message=message, data=data or {}, error=error or message)

    @classmethod
    def cancelled_result(cls, tool_name: str = "") -> "ToolResult":
        """Convenience factory for a cancelled result."""
        msg = f"Tool '{tool_name}' cancelled by user." if tool_name else "Cancelled by user."
        return cls(success=False, message=msg, error="CANCELLED", cancelled=True)

    @classmethod
    def unavailable(cls, resource: str) -> "ToolResult":
        """
        Use when hardware or environment dependency is not present.
        This is distinct from FAIL — the code path works, the hardware does not.
        """
        return cls(
            success=False,
            message=f"[ENVIRONMENT_UNAVAILABLE] {resource} is not available on this machine.",
            error="ENVIRONMENT_UNAVAILABLE",
            data={"resource": resource, "availability": "ENVIRONMENT_UNAVAILABLE"},
        )

    def __bool__(self) -> bool:
        return self.success


# ---------------------------------------------------------------------- #
#  Dispatcher adapter — normalizes legacy str/dict returns into ToolResult #
# ---------------------------------------------------------------------- #

def normalize_result(raw: Any, tool_name: str = "") -> ToolResult:
    """
    Convert whatever a legacy tool function returns into a ToolResult.

    Rules
    -----
    - If already a ToolResult, return as-is.
    - If a dict with a 'success' key, use from_dict().
    - If a non-empty string, infer success from absence of error keywords.
    - If None or empty string, treat as ambiguous success with generic message.
    - If an Exception, treat as failure.

    This lets 33 existing tools continue returning strings while the
    dispatcher, agent loop, and verifier all read a consistent contract.
    """
    if isinstance(raw, ToolResult):
        return raw

    if isinstance(raw, Exception):
        return ToolResult.fail(
            message=f"Tool '{tool_name}' raised an exception: {raw}",
            error=str(raw),
        )

    if isinstance(raw, dict):
        if "success" in raw:
            return ToolResult.from_dict({**raw, "message": raw.get("message", str(raw))})
        # dict without 'success' — treat as data payload, success assumed
        return ToolResult(success=True, message=f"{tool_name} completed.", data=raw)

    # String normalization
    text = str(raw).strip() if raw is not None else ""

    if not text:
        return ToolResult(success=True, message=f"{tool_name} completed.")

    # Heuristic failure detection (matches existing agent_loop.py patterns)
    lower = text.lower()
    failure_signals = [
        "failed", "error:", "could not", "unable to", "exception",
        "not found", "permission denied", "timed out", "cancelled",
        "unavailable", "no device", "unknown tool",
    ]
    cancelled_signals = ["cancelled by user", "operation cancelled", "cancel"]

    if any(s in lower for s in cancelled_signals):
        return ToolResult(success=False, message=text, error="CANCELLED", cancelled=True)

    if any(s in lower for s in failure_signals):
        return ToolResult(success=False, message=text, error=text[:200])

    return ToolResult(success=True, message=text)
