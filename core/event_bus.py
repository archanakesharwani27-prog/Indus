# core/event_bus.py
"""
INDUS Global Event Bus

A thread-safe, in-process pub/sub event stream.
Every subsystem -- UI, agent loop, memory, tools -- publishes to this bus.
The HUD subscribes to display live pipeline progress.

Event flow (master pipeline):
  USER_INPUT -> WAKE_WORD -> COMMAND_ACCEPTED -> LLM_CONNECTED
  -> TOOL_REQUESTED -> SECURITY_CHECK -> TOOL_STARTED -> TOOL_PROGRESS
  -> TOOL_COMPLETED / TOOL_FAILED / TOOL_CANCELLED
  -> VERIFICATION -> MEMORY_UPDATE -> RESPONSE_READY
  -> TTS_STARTED / TTS_COMPLETED -> UI_STATE_CHANGED

Usage:
    from core.event_bus import event_bus, INDUSEvent, E

    # Subscribe (UI or logger):
    event_bus.subscribe(E.TOOL_STARTED, lambda evt: print(evt.source, evt.data))

    # Publish (any module):
    event_bus.publish(E.TOOL_STARTED, source="open_app", data={"app": "Chrome"})
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("IndusEventBus")


# ---------------------------------------------------------------------- #
#  Event name constants                                                    #
# ---------------------------------------------------------------------- #

class E:
    """Named event constants -- use these instead of raw strings."""
    SYSTEM_START         = "SYSTEM_START"
    SYSTEM_STOP          = "SYSTEM_STOP"
    MIC_READY            = "MIC_READY"

    # Voice / wake-word path
    USER_INPUT           = "USER_INPUT"
    WAKE_WORD            = "WAKE_WORD"
    COMMAND_ACCEPTED     = "COMMAND_ACCEPTED"

    # LLM
    LLM_CONNECTED        = "LLM_CONNECTED"
    LLM_FALLBACK         = "LLM_FALLBACK"

    # Tool lifecycle
    TOOL_REQUESTED       = "TOOL_REQUESTED"
    SECURITY_CHECK       = "SECURITY_CHECK"
    TOOL_STARTED         = "TOOL_STARTED"
    TOOL_PROGRESS        = "TOOL_PROGRESS"
    TOOL_COMPLETED       = "TOOL_COMPLETED"
    TOOL_FAILED          = "TOOL_FAILED"
    TOOL_CANCELLED       = "TOOL_CANCELLED"

    # Verification
    VERIFICATION         = "VERIFICATION"
    VERIFICATION_FAILED  = "VERIFICATION_FAILED"

    # Recovery
    RETRY_STARTED        = "RETRY_STARTED"
    REPLAN_STARTED       = "REPLAN_STARTED"

    # Cancellation
    CANCEL_REQUESTED     = "CANCEL_REQUESTED"
    CANCELLED            = "CANCELLED"

    # Memory
    MEMORY_UPDATE        = "MEMORY_UPDATE"

    # Response / TTS
    RESPONSE_READY       = "RESPONSE_READY"
    TTS_STARTED          = "TTS_STARTED"
    TTS_COMPLETED        = "TTS_COMPLETED"

    # UI
    UI_STATE_CHANGED     = "UI_STATE_CHANGED"

    # Generic error
    ERROR                = "ERROR"


# ---------------------------------------------------------------------- #
#  Event dataclass                                                         #
# ---------------------------------------------------------------------- #

@dataclass
class INDUSEvent:
    """
    A single bus event.

    name      : E.* constant
    source    : module / component that published (e.g. "open_app", "main.py")
    data      : arbitrary key-value payload
    timestamp : unix timestamp (float) -- auto-set on creation
    """
    name: str
    source: str
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def __str__(self) -> str:
        ts = time.strftime("%H:%M:%S", time.localtime(self.timestamp))
        data_str = ", ".join(f"{k}={v!r}" for k, v in list(self.data.items())[:3])
        return f"[{ts}] {self.name} | {self.source} | {data_str}"


# ---------------------------------------------------------------------- #
#  Event Bus                                                               #
# ---------------------------------------------------------------------- #

_Handler = Callable[[INDUSEvent], None]


class EventBus:
    """
    Thread-safe publish/subscribe event bus.

    - Subscribers are called synchronously in the publishing thread for
      low-latency UI updates (< 1ms overhead per subscriber).
    - Exceptions in subscribers are caught and logged -- never propagated
      to the publisher.
    - All events are recorded in a bounded ring buffer for inspection.
    """

    HISTORY_LIMIT = 500  # keep last N events

    def __init__(self):
        self._lock = threading.Lock()
        self._subscribers: Dict[str, List[_Handler]] = {}
        self._wildcard: List[_Handler] = []          # subscribe(None, cb) ? all events
        self._history: List[INDUSEvent] = []

    # ------------------------------------------------------------------ #
    #  Subscribe                                                           #
    # ------------------------------------------------------------------ #

    def subscribe(self, event_name: Optional[str], callback: _Handler) -> None:
        """
        Register a callback for a specific event_name.
        Pass event_name=None to receive every event (wildcard).
        """
        with self._lock:
            if event_name is None:
                if callback not in self._wildcard:
                    self._wildcard.append(callback)
            else:
                bucket = self._subscribers.setdefault(event_name, [])
                if callback not in bucket:
                    bucket.append(callback)

    def unsubscribe(self, event_name: Optional[str], callback: _Handler) -> None:
        """Remove a previously registered callback."""
        with self._lock:
            if event_name is None:
                if callback in self._wildcard:
                    self._wildcard.remove(callback)
            else:
                bucket = self._subscribers.get(event_name, [])
                if callback in bucket:
                    bucket.remove(callback)

    # ------------------------------------------------------------------ #
    #  Publish                                                             #
    # ------------------------------------------------------------------ #

    def publish(
        self,
        event_name: str,
        source: str = "unknown",
        data: Dict[str, Any] = None,
    ) -> INDUSEvent:
        """
        Create and dispatch an INDUSEvent to all matching subscribers.
        Returns the created event (useful for testing round-trip latency).
        """
        evt = INDUSEvent(name=event_name, source=source, data=data or {})

        with self._lock:
            # Record in ring buffer
            self._history.append(evt)
            if len(self._history) > self.HISTORY_LIMIT:
                self._history.pop(0)
            # Snapshot handlers to avoid holding lock during dispatch
            specific = list(self._subscribers.get(event_name, []))
            wildcards = list(self._wildcard)

        # Dispatch outside lock
        for handler in specific + wildcards:
            try:
                handler(evt)
            except Exception as exc:
                logger.warning("[EventBus] Handler error for %s: %s", event_name, exc)

        return evt

    # ------------------------------------------------------------------ #
    #  Inspection                                                          #
    # ------------------------------------------------------------------ #

    def get_history(self, event_name: str = None, limit: int = 50) -> List[INDUSEvent]:
        """Return recent events, optionally filtered by name."""
        with self._lock:
            evts = list(self._history)
        if event_name:
            evts = [e for e in evts if e.name == event_name]
        return evts[-limit:]

    def last(self, event_name: str) -> Optional[INDUSEvent]:
        """Return the most recent event of a given name, or None."""
        history = self.get_history(event_name, limit=1)
        return history[-1] if history else None

    def clear_history(self) -> None:
        with self._lock:
            self._history.clear()

    def subscriber_count(self, event_name: str = None) -> int:
        """Return number of subscribers for a given event (or total)."""
        with self._lock:
            if event_name:
                return len(self._subscribers.get(event_name, [])) + len(self._wildcard)
            return sum(len(v) for v in self._subscribers.values()) + len(self._wildcard)


# ---------------------------------------------------------------------- #
#  Global singleton                                                        #
# ---------------------------------------------------------------------- #

event_bus = EventBus()
