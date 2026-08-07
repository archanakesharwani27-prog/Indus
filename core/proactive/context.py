"""
ContextMonitor - Monitors system context for proactive suggestions
"""

import time
import threading
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
from collections import deque


@dataclass
class ContextSnapshot:
    """Single context snapshot."""
    timestamp: float
    active_app: str = ""
    window_title: str = ""
    time_of_day: str = ""
    day_of_week: str = ""
    screen_text: str = ""
    user_idle_seconds: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class ContextMonitor:
    """
    Monitors system context in background for proactive intelligence.
    
    Tracks:
    - Active application/window
    - Time patterns
    - User activity/idle
    - Screen content (optional)
    """
    
    def __init__(self, interval_seconds: float = 30.0):
        self.interval = interval_seconds
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._history: deque = deque(maxlen=1000)
        self._callbacks: List[Callable[[ContextSnapshot], None]] = []
        self._last_snapshot: Optional[ContextSnapshot] = None
        
    def start(self):
        """Start context monitoring."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
    
    def stop(self):
        """Stop context monitoring."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
    
    def add_callback(self, callback: Callable[[ContextSnapshot], None]):
        """Add callback for context changes."""
        self._callbacks.append(callback)
    
    def get_current_context(self) -> Optional[ContextSnapshot]:
        """Get latest context snapshot."""
        return self._last_snapshot
    
    def get_history(self, limit: int = 100) -> List[ContextSnapshot]:
        """Get recent context history."""
        return list(self._history)[-limit:]
    
    def _monitor_loop(self):
        """Main monitoring loop."""
        while self._running:
            try:
                snapshot = self._capture_context()
                if snapshot:
                    self._last_snapshot = snapshot
                    self._history.append(snapshot)
                    
                    # Notify callbacks
                    for callback in self._callbacks:
                        try:
                            callback(snapshot)
                        except Exception:
                            pass
            except Exception:
                pass
            
            time.sleep(self.interval)
    
    def _capture_context(self) -> ContextSnapshot:
        """Capture current system context."""
        now = datetime.now()
        
        # Get active window
        active_app = ""
        window_title = ""
        try:
            from core.system.windows import get_window_manager
            wm = get_window_manager()
            wm.refresh()
            active = wm.get_active_window()
            if active:
                active_app = active.process_name or ""
                window_title = active.title or ""
        except Exception:
            pass
        
        # User idle time (simplified)
        idle_seconds = 0.0
        try:
            import win32api
            idle_ms = win32api.GetTickCount() - win32api.GetLastInputInfo()
            idle_seconds = idle_ms / 1000.0
        except Exception:
            pass
        
        return ContextSnapshot(
            timestamp=time.time(),
            active_app=active_app,
            window_title=window_title,
            time_of_day=now.strftime("%H:%M"),
            day_of_week=now.strftime("%A"),
            user_idle_seconds=idle_seconds
        )


# Global instance
_context_monitor: Optional[ContextMonitor] = None


def get_context_monitor(interval_seconds: float = 30.0) -> ContextMonitor:
    """Get global context monitor."""
    global _context_monitor
    if _context_monitor is None:
        _context_monitor = ContextMonitor(interval_seconds)
    return _context_monitor