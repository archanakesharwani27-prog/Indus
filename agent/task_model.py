# agent/task_model.py
"""
Lightweight, structured Task and Context representations for INDUS Closed-Loop Agent.
"""

import re
import time
import uuid
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional



class TaskStatus(Enum):
    PENDING       = "pending"
    UNDERSTANDING = "understanding"
    PLANNING      = "planning"
    EXECUTING     = "executing"
    VERIFYING     = "verifying"
    RECOVERING    = "recovering"
    COMPLETED     = "completed"
    FAILED        = "failed"
    CANCELLED     = "cancelled"


class ErrorCategory(Enum):
    TRANSIENT            = "transient"
    ENVIRONMENT_ERROR    = "environment_error"
    MISSING_PREREQUISITE = "missing_prerequisite"
    SECURITY_DENIAL      = "security_denial"
    PERMANENT_LIMITATION = "permanent_limitation"
    UNKNOWN_OUTCOME      = "unknown_outcome"


@dataclass
class TaskStep:
    step_id: int
    tool: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    expected_result: str = ""
    critical: bool = True
    status: str = "pending"  # pending, running, success, failed, skipped
    result: Any = None
    verification_details: str = ""
    retries: int = 0
    max_retries: int = 2
    executed_strategy: str = "primary"


@dataclass
class AgentTask:
    task_id: str
    original_user_request: str
    current_goal: str
    steps: List[TaskStep] = field(default_factory=list)
    current_step_idx: int = 0
    status: TaskStatus = TaskStatus.PENDING
    completed_steps: List[Dict[str, Any]] = field(default_factory=list)
    failed_steps: List[Dict[str, Any]] = field(default_factory=list)
    execution_history: List[Dict[str, Any]] = field(default_factory=list)
    retry_count: int = 0
    replan_count: int = 0
    max_replans: int = 3
    timeout_seconds: float = 60.0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    final_output: str = ""
    error_message: str = ""
    cancel_flag: threading.Event = field(default_factory=threading.Event)

    @classmethod
    def create(cls, goal: str, timeout_seconds: float = 60.0) -> "AgentTask":
        return cls(
            task_id=str(uuid.uuid4())[:8],
            original_user_request=goal,
            current_goal=goal,
            timeout_seconds=timeout_seconds,
        )

    def is_cancelled(self) -> bool:
        from core.cancellation import cancellation_manager
        return self.cancel_flag.is_set() or cancellation_manager.is_cancelled()

    def is_timed_out(self) -> bool:
        return (time.time() - self.created_at) > self.timeout_seconds


@dataclass
class AgentContext:
    """Tracks active conversational context across sequential turns."""
    last_app_name: str = ""
    last_target_name: str = ""
    last_action: str = ""
    last_output: str = ""
    recent_entities: List[str] = field(default_factory=list)
    last_task_id: str = ""

    def update_context(self, app: str = "", target: str = "", action: str = "", output: str = ""):
        if app:
            self.last_app_name = app
            if app not in self.recent_entities:
                self.recent_entities.append(app)
        if target:
            self.last_target_name = target
            if target not in self.recent_entities:
                self.recent_entities.append(target)
        if action:
            self.last_action = action
        if output:
            self.last_output = output
        # Keep recent entities list bounded
        if len(self.recent_entities) > 10:
            self.recent_entities = self.recent_entities[-10:]

    def resolve_anaphora(self, text: str) -> str:
        """Resolve pronouns like 'it', 'that', 'them' using context."""
        t_lower = text.lower()
        if not self.last_target_name and not self.last_app_name:
            return text

        candidate = self.last_target_name or self.last_app_name
        # Match standalone 'it', 'usko', 'isko', 'that'
        resolved = re.sub(r"\b(it|that|usko|isko|use|ise)\b", candidate, text, flags=re.IGNORECASE)
        return resolved


# Global singleton conversational context
agent_context = AgentContext()
