# core/avatar/models.py
"""
INDUS Avatar System -- State Models & Enums
Central data structures representing all behavioral, visual, emotional, and physical states.
"""

from dataclasses import dataclass, field
from enum import Enum
import time
from typing import Optional, Tuple, Dict, Any


class EmotionType(str, Enum):
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


class GazeDirection(str, Enum):
    CENTER     = "center"
    LEFT       = "left"
    RIGHT      = "right"
    UP         = "up"
    DOWN       = "down"
    UP_LEFT    = "up_left"
    UP_RIGHT   = "up_right"
    DOWN_LEFT  = "down_left"
    DOWN_RIGHT = "down_right"
    CUSTOM     = "custom"


class BlinkState(str, Enum):
    OPEN    = "open"
    CLOSING = "closing"
    CLOSED  = "closed"
    OPENING = "opening"
    HALF    = "half"


class BlinkType(str, Enum):
    NORMAL   = "normal"
    DOUBLE   = "double"
    THINKING = "thinking"
    EMOTION  = "emotion"


class MouthShape(str, Enum):
    CLOSED  = "closed"
    SLIGHT  = "slight"
    MEDIUM  = "medium"
    WIDE    = "wide"


class VisemeShape(str, Enum):
    """15 distinct mouth positions for phoneme-accurate lip sync."""
    SILENCE     = "silence"       # Closed — pause / end of word
    BILABIAL    = "bilabial"      # M, B, P — lips pressed together
    LABIODENTAL = "labiodental"   # F, V — upper teeth on lower lip
    DENTAL      = "dental"        # TH — tongue tip between teeth
    ALVEOLAR    = "alveolar"      # T, D, S, Z, N, L — slight gap, tongue up
    PALATAL     = "palatal"       # SH, CH, ZH, J — lips forward
    VELAR       = "velar"         # K, G, NG — back open
    VOWEL_OPEN  = "vowel_open"    # A, AH, AW — jaw wide down
    VOWEL_MID   = "vowel_mid"     # E, EH, AY — horizontal stretch
    VOWEL_HIGH  = "vowel_high"    # I, EE — narrow, high
    VOWEL_ROUND = "vowel_round"   # O, OW — rounded
    VOWEL_TIGHT = "vowel_tight"   # OO, U — tight round / pursed
    SCHWA       = "schwa"         # ER, UH — neutral slight open
    LABROUND    = "labround"      # W — rounded lips forward
    GLIDE       = "glide"         # R, Y — transitional


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
class GazeTarget:
    """Represents a 2D gaze coordinate target normalized between -1.0 and +1.0."""
    x: float = 0.0
    y: float = 0.0
    is_tracking: bool = False
    priority: int = 0  # 0: idle micro-gaze, 1: thinking, 2: conversational, 3: explicit target
    label: str = "center"


@dataclass
class LipSyncConfig:
    """Configurable thresholds and filter parameters for voice-driven mouth animation.
    Tuned for 24kHz Gemini Live TTS output (higher energy than 16kHz mic input).
    """
    noise_gate_rms: float = 120.0     # Lower gate — Gemini audio is clean, low noise
    slight_threshold: float = 400.0   # Lips part slightly at this RMS (was 600)
    medium_threshold: float = 1200.0  # Medium opening (was 1800)
    wide_threshold: float = 2800.0    # Wide open (was 3600)
    attack_factor: float = 0.55       # Faster mouth opening response (was 0.45)
    decay_factor: float = 0.18        # Smooth mouth closing (was 0.20)
    sample_rate: int = 24000          # Gemini Live output sample rate


@dataclass
class EmotionProfile:
    """Defines the baseline facial expression modifiers for a specific emotion."""
    emotion: EmotionType
    eyebrow_raise: float = 0.0        # -1.0 (furrowed/angry) to +1.0 (raised/surprised)
    eye_openness: float = 1.0         # 0.5 (squint) to 1.3 (wide open)
    mouth_smile_curve: float = 0.0    # -1.0 (frown) to +1.0 (smile)
    mouth_baseline_open: float = 0.0  # baseline opening without speech (0.0 to 0.4)
    gaze_tendency_y: float = 0.0      # tendency to look up/down in this emotion
    blink_interval_factor: float = 1.0# 0.5 = fast blinking, 2.0 = slow
    pulse_color_hex: str = "#00FFFF"
    transition_speed: float = 3.0     # Speed of transitioning to this emotion


@dataclass
class AvatarState:
    """
    Thread-safe comprehensive representation of the Avatar's current visual state.
    Used by the AvatarRenderer to paint frames at 60 FPS without computing physics.
    """
    # Emotion
    current_emotion: EmotionType = EmotionType.NEUTRAL
    target_emotion: EmotionType = EmotionType.NEUTRAL
    emotion_blend_progress: float = 1.0

    # Operational state
    operational_state: OperationalState = OperationalState.IDLE

    # Gaze coordinates (current interpolated position, normalized -1.0 to +1.0)
    gaze_x: float = 0.0
    gaze_y: float = 0.0
    gaze_direction: GazeDirection = GazeDirection.CENTER
    cursor_tracking_enabled: bool = True

    # Blinking
    blink_state: BlinkState = BlinkState.OPEN
    eyelid_coverage: float = 0.0  # 0.0 = fully open, 1.0 = fully closed

    # Lip-Sync & Mouth
    mouth_openness: float = 0.0   # 0.0 = closed, 1.0 = wide open
    mouth_shape: MouthShape = MouthShape.CLOSED
    mouth_smile_curve: float = 0.0  # -1.0 (frown) to +1.0 (smile), set by EmotionController
    viseme_shape: VisemeShape = VisemeShape.SILENCE  # Current phoneme viseme
    current_rms: float = 0.0
    speaking: bool = False
    listening: bool = False
    thinking: bool = False

    # Procedural FX & HUD
    hud_ring_color: str = "#00FFFF"
    magenta_ring_pulse: float = 0.5
    hologram_glitch_amount: float = 0.0
    audio_level: float = 0.0

    # Timestamps
    last_update_time: float = field(default_factory=time.time)
    animation_enabled: bool = True
