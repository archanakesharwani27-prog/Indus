"""
RoutineLearner - Detects user patterns and routines
"""

import time
import json
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, Counter
from datetime import datetime, timedelta
import sqlite3
import os


@dataclass
class RoutinePattern:
    """Detected routine pattern."""
    name: str
    trigger: Dict[str, Any]  # time, app, day, etc.
    actions: List[Dict[str, Any]]  # sequence of actions
    confidence: float
    occurrences: int
    last_seen: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RoutineSuggestion:
    """Suggestion based on learned routine."""
    pattern: RoutinePattern
    suggested_actions: List[Dict[str, Any]]
    reason: str
    confidence: float


class RoutineLearner:
    """
    Learns user routines from context history.
    
    Detects patterns like:
    - "At 9am on weekdays, user opens VS Code + Terminal"
    - "After opening Chrome, user opens WhatsApp Web"
    - "At 1pm, user checks email"
    """
    
    def __init__(self, db_path: str = "routines.db", min_occurrences: int = 3):
        self.db_path = db_path
        self.min_occurrences = min_occurrences
        self._patterns: List[RoutinePattern] = []
        self._init_db()
        self._load_patterns()
    
    def _init_db(self):
        """Initialize database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE,
                    trigger TEXT,
                    actions TEXT,
                    confidence REAL,
                    occurrences INTEGER,
                    last_seen REAL,
                    metadata TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL,
                    event_type TEXT,
                    data TEXT
                )
            """)
    
    def _load_patterns(self):
        """Load patterns from database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT * FROM patterns")
            for row in cursor.fetchall():
                pattern = RoutinePattern(
                    name=row[1],
                    trigger=json.loads(row[2]),
                    actions=json.loads(row[3]),
                    confidence=row[4],
                    occurrences=row[5],
                    last_seen=row[6],
                    metadata=json.loads(row[7]) if row[7] else {}
                )
                self._patterns.append(pattern)
    
    def record_event(self, event_type: str, data: Dict[str, Any]):
        """Record an event for pattern learning."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO events (timestamp, event_type, data) VALUES (?, ?, ?)",
                (time.time(), event_type, json.dumps(data))
            )
    
    def record_app_launch(self, app_name: str, window_title: str = ""):
        """Record app launch event."""
        self.record_event("app_launch", {
            "app": app_name,
            "window": window_title,
            "time": datetime.now().strftime("%H:%M"),
            "day": datetime.now().strftime("%A")
        })
    
    def record_command(self, command: str, params: Dict[str, Any] = None):
        """Record user command."""
        self.record_event("command", {
            "command": command,
            "params": params or {},
            "time": datetime.now().strftime("%H:%M"),
            "day": datetime.now().strftime("%A")
        })
    
    def analyze_patterns(self, lookback_days: int = 7) -> List[RoutinePattern]:
        """Analyze events and detect patterns."""
        cutoff = time.time() - (lookback_days * 86400)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT timestamp, event_type, data FROM events WHERE timestamp > ? ORDER BY timestamp",
                (cutoff,)
            )
            events = []
            for row in cursor.fetchall():
                events.append({
                    "timestamp": row[0],
                    "type": row[1],
                    "data": json.loads(row[2])
                })
        
        # Group by time windows (30 min)
        time_windows = defaultdict(list)
        for event in events:
            dt = datetime.fromtimestamp(event["timestamp"])
            window_key = dt.replace(minute=(dt.minute // 30) * 30, second=0, microsecond=0)
            time_windows[window_key].append(event)
        
        # Find recurring sequences
        sequences = Counter()
        for window, window_events in time_windows.items():
            # Create sequence signature
            sig = tuple(f"{e['type']}:{e['data'].get('app', e['data'].get('command', ''))}" 
                       for e in window_events if e['type'] in ('app_launch', 'command'))
            if len(sig) >= 2:
                sequences[sig] += 1
        
        # Create patterns from frequent sequences
        new_patterns = []
        for seq, count in sequences.most_common():
            if count >= self.min_occurrences:
                # Check if already known
                existing = next((p for p in self._patterns if self._seq_matches(p.actions, seq)), None)
                if not existing:
                    pattern = self._create_pattern(seq, count)
                    new_patterns.append(pattern)
                    self._save_pattern(pattern)
        
        self._patterns.extend(new_patterns)
        return new_patterns
    
    def _seq_matches(self, actions: List[Dict], seq: tuple) -> bool:
        """Check if pattern actions match sequence."""
        if len(actions) != len(seq):
            return False
        for action, sig in zip(actions, seq):
            if f"{action.get('type')}:{action.get('app', action.get('command', ''))}" != sig:
                return False
        return True
    
    def _create_pattern(self, seq: tuple, count: int) -> RoutinePattern:
        """Create pattern from sequence."""
        actions = []
        for sig in seq:
            parts = sig.split(":", 1)
            actions.append({"type": parts[0], "target": parts[1]})
        
        # Determine trigger from first action
        first = actions[0]
        trigger = {"type": "time_based"}
        if first["type"] == "app_launch":
            trigger["after_app"] = first["target"]
        
        return RoutinePattern(
            name=f"routine_{len(self._patterns) + 1}",
            trigger=trigger,
            actions=actions,
            confidence=min(0.5 + (count * 0.1), 0.95),
            occurrences=count,
            last_seen=time.time()
        )
    
    def _save_pattern(self, pattern: RoutinePattern):
        """Save pattern to database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO patterns 
                (name, trigger, actions, confidence, occurrences, last_seen, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    pattern.name,
                    json.dumps(pattern.trigger),
                    json.dumps(pattern.actions),
                    pattern.confidence,
                    pattern.occurrences,
                    pattern.last_seen,
                    json.dumps(pattern.metadata)
                )
            )
    
    def get_suggestions(self, current_context: Dict[str, Any]) -> List[RoutineSuggestion]:
        """Get routine suggestions for current context."""
        suggestions = []
        current_time = datetime.now().strftime("%H:%M")
        current_day = datetime.now().strftime("%A")
        current_app = current_context.get("active_app", "")
        
        for pattern in self._patterns:
            if pattern.confidence < 0.6:
                continue
            
            # Check if trigger matches
            match_score = self._match_trigger(pattern, current_context)
            if match_score > 0.5:
                # Suggest next actions not yet done
                suggested = self._get_next_actions(pattern, current_context)
                if suggested:
                    suggestions.append(RoutineSuggestion(
                        pattern=pattern,
                        suggested_actions=suggested,
                        reason=f"Learned routine: {' -> '.join(a['target'] for a in pattern.actions)}",
                        confidence=pattern.confidence * match_score
                    ))
        
        return sorted(suggestions, key=lambda s: s.confidence, reverse=True)
    
    def _match_trigger(self, pattern: RoutinePattern, context: Dict) -> float:
        """Match pattern trigger against current context."""
        score = 0.0
        trigger = pattern.trigger
        
        if trigger.get("type") == "time_based":
            # Time-based matching would go here
            score += 0.3
        
        if "after_app" in trigger:
            if context.get("active_app") == trigger["after_app"]:
                score += 0.7
        
        return min(score, 1.0)
    
    def _get_next_actions(self, pattern: RoutinePattern, context: Dict) -> List[Dict]:
        """Get next actions in routine not yet performed."""
        done_apps = set()
        # Would check recent history for what's already done
        # For now, return all actions
        return pattern.actions
    
    def get_stats(self) -> Dict[str, Any]:
        """Get learner statistics."""
        return {
            "total_patterns": len(self._patterns),
            "high_confidence": len([p for p in self._patterns if p.confidence > 0.7]),
            "db_path": self.db_path
        }


# Global instance
_routine_learner: Optional[RoutineLearner] = None


def get_routine_learner(db_path: str = "routines.db") -> RoutineLearner:
    """Get global routine learner."""
    global _routine_learner
    if _routine_learner is None:
        _routine_learner = RoutineLearner(db_path)
    return _routine_learner