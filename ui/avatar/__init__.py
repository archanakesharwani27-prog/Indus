# ui/avatar/__init__.py
"""
INDUS Avatar System -- Public UI Avatar Module
"""

from ui.avatar.avatar_state import AvatarState, Emotion, MouthState, Gaze, OperationalState
from ui.avatar.emotion_manager import IndusEmotionFaceManager, parse_emotion_tag
from ui.avatar.gaze_controller import GazeController
from ui.avatar.blink_controller import BlinkController
from ui.avatar.lipsync_controller import LipSyncController, LipSyncConfig, RMSFilter, calculate_rms, classify_mouth
from ui.avatar.assets import AssetResolver
from ui.avatar.widget import AvatarWidget

__all__ = [
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
