# core/avatar/__init__.py
"""
INDUS Avatar System -- Public Interface
"""

from core.avatar.models import (
    AvatarState as CoreAvatarState, EmotionType, GazeDirection, BlinkState, BlinkType,
    MouthShape, OperationalState as CoreOperationalState, GazeTarget, LipSyncConfig as CoreLipSyncConfig, EmotionProfile
)
from core.avatar.controller import AvatarController
from core.avatar.renderer import AvatarRenderer
from core.avatar.events import AvatarEvents, emit_avatar_event

from core.avatar.avatar_state import AvatarState, Emotion, MouthState, Gaze, OperationalState
from core.avatar.emotion_manager import IndusEmotionFaceManager, parse_emotion_tag
from core.avatar.gaze_controller import GazeController
from core.avatar.blink_controller import BlinkController
from core.avatar.lipsync_controller import LipSyncController, LipSyncConfig, RMSFilter, calculate_rms, classify_mouth
from core.avatar.assets import AssetResolver
from core.avatar.widget import AvatarWidget

__all__ = [
    "CoreAvatarState",
    "EmotionType",
    "GazeDirection",
    "BlinkState",
    "BlinkType",
    "MouthShape",
    "CoreOperationalState",
    "GazeTarget",
    "CoreLipSyncConfig",
    "EmotionProfile",
    "AvatarController",
    "AvatarRenderer",
    "AvatarEvents",
    "emit_avatar_event",
    "AvatarState",
    "Emotion",
    "MouthState",
    "Gaze",
    "OperationalState",
    "IndusEmotionFaceManager",
    "parse_emotion_tag",
    "GazeController",
    "BlinkController",
    "LipSyncController",
    "LipSyncConfig",
    "RMSFilter",
    "calculate_rms",
    "classify_mouth",
    "AssetResolver",
    "AvatarWidget",
]
