"""
Proactive Package - Proactive intelligence and suggestions
"""

from core.proactive.context import ContextMonitor, ContextSnapshot, get_context_monitor
from core.proactive.routines import RoutineLearner, RoutinePattern, RoutineSuggestion, get_routine_learner
from core.proactive.suggestions import (
    SuggestionEngine, 
    Suggestion, 
    SuggestionType, 
    get_suggestion_engine
)

__all__ = [
    "ContextMonitor",
    "ContextSnapshot", 
    "get_context_monitor",
    "RoutineLearner",
    "RoutinePattern",
    "RoutineSuggestion",
    "get_routine_learner",
    "SuggestionEngine",
    "Suggestion",
    "SuggestionType",
    "get_suggestion_engine",
]