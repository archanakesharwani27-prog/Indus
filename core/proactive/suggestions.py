"""
SuggestionEngine - Generates proactive suggestions based on context and routines
"""

import time
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from enum import Enum
import threading

from core.proactive.context import ContextMonitor, ContextSnapshot, get_context_monitor
from core.proactive.routines import RoutineLearner, RoutineSuggestion, get_routine_learner


class SuggestionType(Enum):
    """Types of proactive suggestions."""
    ROUTINE = "routine"           # Based on learned routines
    CONTEXTUAL = "contextual"     # Based on current context
    TIME_BASED = "time_based"     # Time-based reminders
    IDLE_BASED = "idle_based"     # When user is idle
    CALENDAR = "calendar"         # Calendar-based (future)


@dataclass
class Suggestion:
    """Proactive suggestion."""
    id: str
    type: SuggestionType
    title: str
    description: str
    actions: List[Dict[str, Any]]  # Executable actions
    confidence: float
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    dismissed: bool = False
    executed: bool = False


class SuggestionEngine:
    """
    Generates proactive suggestions by combining:
    - Context monitoring (what's happening now)
    - Routine learning (what user typically does)
    - Time/calendar awareness
    """
    
    def __init__(
        self,
        context_interval: float = 30.0,
        suggestion_cooldown: float = 300.0  # 5 min between suggestions
    ):
        self.context_monitor = get_context_monitor(context_interval)
        self.routine_learner = get_routine_learner()
        self.suggestion_cooldown = suggestion_cooldown
        
        self._suggestions: List[Suggestion] = []
        self._last_suggestion_time = 0.0
        self._callbacks: List[Callable[[Suggestion], None]] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None
        
        # Register context callback
        self.context_monitor.add_callback(self._on_context_change)
    
    def start(self):
        """Start suggestion engine."""
        if self._running:
            return
        self.context_monitor.start()
        self._running = True
        self._thread = threading.Thread(target=self._suggestion_loop, daemon=True)
        self._thread.start()
    
    def stop(self):
        """Stop suggestion engine."""
        self._running = False
        self.context_monitor.stop()
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
    
    def add_callback(self, callback: Callable[[Suggestion], None]):
        """Add callback for new suggestions."""
        self._callbacks.append(callback)
    
    def get_pending_suggestions(self, limit: int = 5) -> List[Suggestion]:
        """Get pending (not dismissed/executed) suggestions."""
        pending = [s for s in self._suggestions if not s.dismissed and not s.executed]
        return sorted(pending, key=lambda s: s.confidence, reverse=True)[:limit]
    
    def dismiss_suggestion(self, suggestion_id: str):
        """Dismiss a suggestion."""
        for s in self._suggestions:
            if s.id == suggestion_id:
                s.dismissed = True
                break
    
    def execute_suggestion(self, suggestion_id: str) -> bool:
        """Mark suggestion as executed."""
        for s in self._suggestions:
            if s.id == suggestion_id:
                s.executed = True
                return True
        return False
    
    def _on_context_change(self, snapshot: ContextSnapshot):
        """Handle context change - generate suggestions."""
        now = time.time()
        if now - self._last_suggestion_time < self.suggestion_cooldown:
            return
        
        suggestions = self._generate_suggestions(snapshot)
        for suggestion in suggestions:
            self._suggestions.append(suggestion)
            for callback in self._callbacks:
                try:
                    callback(suggestion)
                except Exception:
                    pass
        
        if suggestions:
            self._last_suggestion_time = now
    
    def _generate_suggestions(self, snapshot: ContextSnapshot) -> List[Suggestion]:
        """Generate suggestions from current context."""
        suggestions = []
        context_dict = {
            "active_app": snapshot.active_app,
            "window_title": snapshot.window_title,
            "time_of_day": snapshot.time_of_day,
            "day_of_week": snapshot.day_of_week,
            "idle_seconds": snapshot.user_idle_seconds
        }
        
        # 1. Routine-based suggestions
        routine_suggestions = self.routine_learner.get_suggestions(context_dict)
        for rs in routine_suggestions:
            if rs.confidence > 0.6:
                suggestions.append(Suggestion(
                    id=f"routine_{int(time.time() * 1000)}",
                    type=SuggestionType.ROUTINE,
                    title=f"Routine: {rs.pattern.name}",
                    description=rs.reason,
                    actions=rs.suggested_actions,
                    confidence=rs.confidence,
                    timestamp=time.time(),
                    metadata={"pattern": rs.pattern.name}
                ))
        
        # 2. Idle-based suggestions
        if snapshot.user_idle_seconds > 300:  # 5 min idle
            suggestions.append(self._create_idle_suggestion(snapshot))
        
        # 3. Time-based suggestions
        time_suggestions = self._generate_time_suggestions(snapshot)
        suggestions.extend(time_suggestions)
        
        # 4. Contextual suggestions
        contextual = self._generate_contextual_suggestions(snapshot)
        suggestions.extend(contextual)
        
        return suggestions
    
    def _create_idle_suggestion(self, snapshot: ContextSnapshot) -> Suggestion:
        """Create suggestion for idle user."""
        return Suggestion(
            id=f"idle_{int(time.time() * 1000)}",
            type=SuggestionType.IDLE_BASED,
            title="You've been away",
            description=f"Idle for {int(snapshot.user_idle_seconds/60)} minutes. Want a summary?",
            actions=[{"type": "command", "command": "summarize last hour"}],
            confidence=0.7,
            timestamp=time.time()
        )
    
    def _generate_time_suggestions(self, snapshot: ContextSnapshot) -> List[Suggestion]:
        """Generate time-based suggestions."""
        suggestions = []
        hour = int(snapshot.time_of_day.split(":")[0])
        
        # Morning routine
        if hour == 9 and snapshot.day_of_week in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]:
            suggestions.append(Suggestion(
                id=f"time_morning_{int(time.time() * 1000)}",
                type=SuggestionType.TIME_BASED,
                title="Good morning!",
                description="Typical work start time. Open your workspace?",
                actions=[
                    {"type": "command", "command": "open vscode"},
                    {"type": "command", "command": "open terminal"}
                ],
                confidence=0.6,
                timestamp=time.time()
            ))
        
        # Lunch break
        if hour == 13:
            suggestions.append(Suggestion(
                id=f"time_lunch_{int(time.time() * 1000)}",
                type=SuggestionType.TIME_BASED,
                title="Lunch time",
                description="Take a break? I can remind you in 30 min.",
                actions=[{"type": "command", "command": "remind me in 30 minutes"}],
                confidence=0.5,
                timestamp=time.time()
            ))
        
        return suggestions
    
    def _generate_contextual_suggestions(self, snapshot: ContextSnapshot) -> List[Suggestion]:
        """Generate contextual suggestions based on active app."""
        suggestions = []
        app = snapshot.active_app.lower()
        
        if "chrome" in app or "edge" in app or "browser" in app:
            if "whatsapp" in snapshot.window_title.lower():
                suggestions.append(Suggestion(
                    id=f"ctx_wa_{int(time.time() * 1000)}",
                    type=SuggestionType.CONTEXTUAL,
                    title="WhatsApp Web detected",
                    description="Want to send a message or check chats?",
                    actions=[
                        {"type": "command", "command": "send whatsapp to Ansh hello"},
                        {"type": "command", "command": "read whatsapp messages"}
                    ],
                    confidence=0.6,
                    timestamp=time.time()
                ))
        
        elif "code" in app or "vscode" in app:
            suggestions.append(Suggestion(
                id=f"ctx_code_{int(time.time() * 1000)}",
                type=SuggestionType.CONTEXTUAL,
                title="VS Code active",
                description="Need terminal, git, or run command?",
                actions=[
                    {"type": "command", "command": "open terminal"},
                    {"type": "command", "command": "git status"}
                ],
                confidence=0.5,
                timestamp=time.time()
            ))
        
        return suggestions
    
    def _suggestion_loop(self):
        """Background loop for periodic suggestion generation."""
        while self._running:
            # Periodically re-analyze routines
            try:
                self.routine_learner.analyze_patterns(lookback_days=7)
            except Exception:
                pass
            time.sleep(3600)  # Every hour
    
    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            "total_suggestions": len(self._suggestions),
            "pending": len(self.get_pending_suggestions()),
            "routine_stats": self.routine_learner.get_stats(),
            "context_running": self.context_monitor._running
        }


# Global instance
_suggestion_engine: Optional[SuggestionEngine] = None


def get_suggestion_engine() -> SuggestionEngine:
    """Get global suggestion engine."""
    global _suggestion_engine
    if _suggestion_engine is None:
        _suggestion_engine = SuggestionEngine()
    return _suggestion_engine