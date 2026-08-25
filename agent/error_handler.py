# agent/error_handler.py
"""
INDUS Error Diagnostic, Classification & Recovery Engine
Classifies step execution errors, enforces safe retry bounds, prevents duplicate failed strategies,
and produces concrete alternative recovery strategies without infinite loops.
"""

import json
import logging
import re
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from agent.task_model import ErrorCategory, TaskStep

logger = logging.getLogger("IndusErrorHandler")

# Destructive action keywords that must NEVER be automatically retried
DESTRUCTIVE_KEYWORDS = [
    "delete", "remove", "kill", "format", "wipe", "drop",
    "clear_all", "shutdown", "reboot", "restart", "erase", "uninstall"
]

# Known transient errors that are safe to retry
TRANSIENT_PATTERNS = [
    r"timeout", r"timed out", r"connection reset", r"temporarily unavailable",
    r"busy", r"lock", r"try again", r"rate limit", r"429", r"503", r"504",
    r"window focus", r"not foreground"
]


def is_destructive_step(step: Any) -> bool:
    """Check if the given step involves a destructive or high-risk operation."""
    if isinstance(step, str):
        desc = step.lower()
    elif isinstance(step, TaskStep):
        desc = f"{step.tool} {step.description} {json.dumps(step.parameters)}".lower()
    else:
        desc = str(step).lower()
    return any(k in desc for k in DESTRUCTIVE_KEYWORDS)


def classify_error(
    step: Any,
    error_message: str = "",
    attempt: int = 1,
) -> Tuple[ErrorCategory, str, str]:
    """
    Classifies error and determines next recovery action.
    Returns: (category: ErrorCategory, reason: str, alternative_suggestion: str)
    """
    # Allow flexible argument order: (error_message, step) or (step, error_message)
    if isinstance(step, str) and isinstance(error_message, (TaskStep, str)) and error_message != "":
        if not isinstance(error_message, str) or any(k in error_message.lower() for k in ["error", "failed", "timeout", "not found"]):
            # step is error message, error_message is tool/step
            step, error_message = error_message, step

    err_lower = (str(error_message) or "").lower()
    step_obj = step if isinstance(step, TaskStep) else TaskStep(tool=str(step), description=str(step))


    # 1. Security or Policy Denials
    if "security" in err_lower or "blocked" in err_lower or "unauthorized" in err_lower or "pin" in err_lower:
        return (
            ErrorCategory.SECURITY_DENIAL,
            f"Action was blocked by security policy: {error_message}",
            "Stop execution and request user authorization.",
        )

    # 2. Destructive Action Protection
    if is_destructive_step(step_obj):
        return (
            ErrorCategory.PERMANENT_LIMITATION,
            f"Destructive action failed and cannot be automatically retried: {error_message}",
            "Notify user of failure.",
        )

    # 3. Transient Errors (Network, Focus, Brief lock)
    if any(re.search(p, err_lower) for p in TRANSIENT_PATTERNS) and attempt < getattr(step_obj, "max_retries", 2):
        return (
            ErrorCategory.TRANSIENT,
            f"Transient system delay or timeout: {error_message[:120]}",
            f"Wait 0.5s and perform safe retry (attempt {attempt + 1}/{getattr(step_obj, 'max_retries', 2)}).",
        )

    # 4. Element Not Found / Visual Misses ? Alternative Strategy
    if "not found" in err_lower or "coordinates" in err_lower or "cannot click" in err_lower or "ambiguous" in err_lower:
        curr_strategy = getattr(step_obj, "executed_strategy", "primary")

        if curr_strategy == "primary":
            alt = "Use Vision Grounding (vision_find_element) with broader contextual description."
        elif curr_strategy == "ocr":
            alt = "Use Multimodal Vision Grounding (vision_click)."
        else:
            alt = "Try keyboard shortcut or application window focus."
        return (
            ErrorCategory.ENVIRONMENT_ERROR,
            f"UI element was not found or failed visual verification: {error_message[:120]}",
            alt,
        )

    # 5. Missing Prerequisite (e.g. process not running)
    if "not running" in err_lower or "not open" in err_lower or "window not found" in err_lower:
        return (
            ErrorCategory.MISSING_PREREQUISITE,
            f"Required application or window is not currently open: {error_message[:120]}",
            "Launch application first via 'open_app'.",
        )

    # 6. Default Fallback
    return (
        ErrorCategory.ENVIRONMENT_ERROR,
        f"Step failed execution: {error_message[:120]}",
        "Re-plan remaining task using an alternative tool.",
    )


def generate_alternative_step(failed_step: TaskStep, error_category: ErrorCategory, alt_suggestion: str) -> Optional[TaskStep]:
    """
    Generates a concrete alternative step without repeating the failed strategy.
    """
    if error_category == ErrorCategory.SECURITY_DENIAL or is_destructive_step(failed_step):
        return None

    # Alternative for computer_control / vision_click failures
    if failed_step.tool in ("computer_control", "vision_click"):
        target = failed_step.parameters.get("target") or failed_step.parameters.get("description") or failed_step.description
        if failed_step.executed_strategy == "primary":
            # Switch to vision_click with high detail
            new_step = TaskStep(
                step_id=failed_step.step_id,
                tool="vision_click",
                description=f"Visually locate and click {target}",
                parameters={"target": target, "context": "Try searching broader screen area"},
                expected_result=failed_step.expected_result,
                executed_strategy="vision_grounding",
                max_retries=1,
            )
            return new_step
        elif failed_step.executed_strategy == "vision_grounding":
            # Switch to keyboard enter / hotkey fallback
            new_step = TaskStep(
                step_id=failed_step.step_id,
                tool="computer_control",
                description=f"Press Enter or Tab to activate {target}",
                parameters={"action": "press", "key": "enter"},
                expected_result=failed_step.expected_result,
                executed_strategy="keyboard_fallback",
                max_retries=1,
            )
            return new_step

    # Alternative for open_app failures (try cmd_control / browser_control)
    if failed_step.tool == "open_app":
        app = failed_step.parameters.get("app_name", "")
        new_step = TaskStep(
            step_id=failed_step.step_id,
            tool="cmd_control",
            description=f"Launch {app} via system shell command",
            parameters={"task": f"start {app}"},
            expected_result=failed_step.expected_result,
            executed_strategy="shell_fallback",
            max_retries=1,
        )
        return new_step

    return None