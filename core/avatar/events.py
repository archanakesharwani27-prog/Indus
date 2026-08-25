# core/avatar/events.py
"""
INDUS Avatar System -- Event Bridges & Telemetry
Integrates avatar state changes with INDUS EventBus.
"""

from typing import Callable, Dict, Any, List
from core.event_bus import event_bus, E


class AvatarEvents:
    EMOTION_CHANGED       = "AVATAR_EMOTION_CHANGED"
    GAZE_TARGET_CHANGED   = "AVATAR_GAZE_CHANGED"
    BLINK_STARTED         = "AVATAR_BLINK_STARTED"
    BLINK_FINISHED        = "AVATAR_BLINK_FINISHED"
    SPEECH_STARTED        = "AVATAR_SPEECH_STARTED"
    SPEECH_FINISHED       = "AVATAR_SPEECH_FINISHED"
    STATE_CHANGED         = "AVATAR_STATE_CHANGED"
    VISION_TARGET_CHANGED = "AVATAR_VISION_TARGET_CHANGED"


def emit_avatar_event(event_name: str, data: Dict[str, Any] = None):
    """Publish an avatar telemetry event to the central event bus."""
    try:
        event_bus.publish(event_name, source="avatar", data=data or {})
    except Exception:
        pass
