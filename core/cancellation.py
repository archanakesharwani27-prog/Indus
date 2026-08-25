# core/cancellation.py
"""
INDUS Voice Interruption & True Task Cancellation Subsystem
Provides fast deterministic interruption detection, thread-safe CancellationToken,
and callback propagation for immediate TTS halting, tool cancellation, and queue flushing.
"""

import re
import threading
import time
from typing import Callable, Optional, List

# Deterministic keywords for voice & text interruption
STOP_PATTERNS = [
    r"\bstop\b",
    r"\bcancel\b",
    r"\babort\b",
    r"\bnever\s*mind\b",
    r"\bshut\s*up\b",
    r"\bruko\b",
    r"\bbas\b",
    r"\bchup\b",
    r"\bband\s*karo\b",
    r"\bchup\s*ho\s*jao\b",
    r"\bpause\b",
    r"\bquit\b",
]

_COMPILED_STOP_PATTERNS = [re.compile(p, re.IGNORECASE) for p in STOP_PATTERNS]


# Words that indicate a media/tool command (NOT an assistant cancellation)
MEDIA_EXCLUSION_WORDS = {
    "song", "video", "music", "gaana", "gana", "youtube", "media",
    "playback", "movie", "audio", "track", "playing", "volume", "sound",
    "screen", "mic", "window", "tab", "app", "application", "browser",
    "pc", "system", "computer", "wifi", "bluetooth", "brightness"
}

def is_stop_phrase(text: str) -> bool:
    """
    Fast deterministic check for explicit user cancellation commands.
    Ensures short phrases like 'stop', 'indus stop', 'cancel that', 'ruko' trigger immediately,
    while avoiding false positives on media commands (e.g. 'pause song', 'stop the music').
    """
    if not text:
        return False
    t = text.strip().lower()
    words = t.split()

    # If the user is referring to a song, video, app, or system feature, it is NOT an assistant cancellation
    if any(w in MEDIA_EXCLUSION_WORDS for w in words):
        return False

    # Fast match for 1-5 word explicit stop commands
    if len(words) <= 5:
        return any(p.search(t) for p in _COMPILED_STOP_PATTERNS)

    # If longer sentence starts with explicit imperative stop command
    if words and words[0] in ("stop", "cancel", "abort", "ruko", "bas", "chup"):
        return True
    return False


class CancelledError(Exception):
    """
    Raised by raise_if_cancelled() inside long-running tools.
    Callers catch this and return a ToolResult.cancelled_result().
    """
    pass


class CancellationManager:
    """
    Thread-safe cooperative cancellation manager.
    Tracks active task, triggers registered callbacks, and exposes is_cancelled flags.
    """

    def __init__(self):
        self._cancel_event = threading.Event()
        self._current_task_name: Optional[str] = None
        self._lock = threading.Lock()
        self._callbacks: List[Callable[[str], None]] = []

    def request_cancellation(self, reason: str = "User voice interruption"):
        """Trigger cancellation across all registered handlers and set cancel event."""
        with self._lock:
            self._cancel_event.set()
            callbacks_snapshot = list(self._callbacks)
            task = self._current_task_name

        print(f"[CancellationManager] Cancellation requested (Task: '{task}', Reason: '{reason}')")

        # Publish to global event bus (non-blocking, best-effort)
        try:
            from core.event_bus import event_bus, E
            event_bus.publish(E.CANCEL_REQUESTED, source="cancellation_manager",
                              data={"task": task, "reason": reason})
        except Exception:
            pass

        for cb in callbacks_snapshot:
            try:
                cb(reason)
            except Exception as e:
                print(f"[CancellationManager] Callback error: {e}")

    def register_callback(self, cb: Callable[[str], None]):
        """Register a callback to be called on cancellation (e.g. TTS flush, thread abort)."""
        with self._lock:
            if cb not in self._callbacks:
                self._callbacks.append(cb)

    def unregister_callback(self, cb: Callable[[str], None]):
        """Unregister a cancellation callback."""
        with self._lock:
            if cb in self._callbacks:
                self._callbacks.remove(cb)

    def is_cancelled(self) -> bool:
        """Check if cancellation has been requested for the current turn/task."""
        return self._cancel_event.is_set()

    def raise_if_cancelled(self, tool_name: str = "") -> None:
        """
        Cooperative checkpoint for long-running tools.
        Call at meaningful loop boundaries — between iterations, before I/O operations.
        Raises CancelledError if cancellation has been requested.

        Example usage in a tool:
            for result in search_results:
                cancellation_manager.raise_if_cancelled("deep_research")
                process(result)
        """
        if self._cancel_event.is_set():
            raise CancelledError(
                f"Tool '{tool_name}' cancelled by user." if tool_name else "Cancelled by user."
            )

    def reset(self):
        """Reset cancellation state for a new conversational turn or task."""
        with self._lock:
            self._cancel_event.clear()
            self._current_task_name = None

    def set_active_task(self, task_name: str):
        """Mark an active task name and reset cancel token for the new task."""
        with self._lock:
            self._cancel_event.clear()
            self._current_task_name = task_name

    def clear_active_task(self):
        """Clear active task after completion."""
        with self._lock:
            self._current_task_name = None

    @property
    def active_task(self) -> Optional[str]:
        with self._lock:
            return self._current_task_name


# Global singleton instance
cancellation_manager = CancellationManager()
