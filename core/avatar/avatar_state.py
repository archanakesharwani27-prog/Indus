# core/avatar/avatar_state.py
"""
INDUS Avatar System -- Authoritative Avatar State
Single authoritative state representation preventing conflicting controller states.
"""

from dataclasses import dataclass, field
from enum import Enum
import time


class Emotion(str, Enum):
    NEUTRAL   = "neutral"
    HAPPY     = "happy"
    SAD       = "sad"
    THINKING  = "thinking"
    SURPRISED = "surprised"
    ANGRY     = "angry"
    CONFUSED  = "confused"
    CONCERNED = "concerned"
    CALM      = "calm"
    EXCITED   = "excited"


class MouthState(str, Enum):
    BLANK  = "blank"
    SLIGHT = "slight"
    MEDIUM = "medium"
    WIDE   = "wide"


class Gaze(str, Enum):
    CENTER = "center"
    LEFT   = "left"
    RIGHT  = "right"
    UP     = "up"
    DOWN   = "down"


class OperationalState(str, Enum):
    IDLE       = "idle"
    LISTENING  = "listening"
    THINKING   = "thinking"
    SPEAKING   = "speaking"
    PROCESSING = "processing"
    SUCCESS    = "success"
    WARNING    = "warning"
    ERROR      = "error"
    STANDBY    = "standby"
    MUTED      = "muted"


@dataclass
class AvatarState:
    """Authoritative state for the complete INDUS Avatar subsystem."""
    emotion: Emotion = Emotion.NEUTRAL
    blinking: bool = False
    gaze: str = "center"
    mouth: MouthState = MouthState.BLANK
    speaking: bool = False
    listening: bool = False
    thinking: bool = False
    operational_state: OperationalState = OperationalState.IDLE
    rms: float = 0.0
    last_updated: float = field(default_factory=time.time)
