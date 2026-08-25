# ui/avatar/emotion_manager.py
"""
INDUS Avatar System -- Master Emotion Face Manager
Authoritative controller managing expression baselines, gaze, blinking, and audio-driven lip-sync.
"""

from typing import Optional, Dict, Any
from PyQt6.QtCore import QObject, pyqtSignal

from ui.avatar.avatar_state import AvatarState, Emotion, MouthState, OperationalState
from ui.avatar.assets import AssetResolver
from ui.avatar.blink_controller import BlinkController
from ui.avatar.gaze_controller import GazeController
from ui.avatar.lipsync_controller import LipSyncController, LipSyncConfig


def parse_emotion_tag(text: str) -> Emotion:
    """
    Parses compatibility emotion tags like '[HAPPY]', '[THINKING]', '[SAD]' from assistant responses.
    """
    mapping = {
        "[NEUTRAL]":   Emotion.NEUTRAL,
        "[HAPPY]":     Emotion.HAPPY,
        "[SAD]":       Emotion.SAD,
        "[THINKING]":  Emotion.THINKING,
        "[SURPRISED]": Emotion.SURPRISED,
        "[ANGRY]":     Emotion.ANGRY,
        "[CONFUSED]":  Emotion.CONFUSED,
        "[CONCERNED]": Emotion.CONCERNED,
        "[CALM]":      Emotion.CALM,
        "[EXCITED]":   Emotion.EXCITED,
    }
    for tag, em in mapping.items():
        if tag in text:
            return em
    return Emotion.NEUTRAL


class IndusEmotionFaceManager(QObject):
    """
    Authoritative controller for avatar expressions, assets, gaze, blinking, and lip-sync.
    """

    face_updated = pyqtSignal()
    mouth_updated = pyqtSignal()

    def __init__(self, avatar_widget=None, config: Optional[LipSyncConfig] = None):
        super().__init__()
        self.avatar = avatar_widget
        self.state = AvatarState()
        self.assets = AssetResolver()

        self.gaze = GazeController(self)
        self.blink = BlinkController(self)
        self.lipsync = LipSyncController(self, config=config)

        self.set_emotion(Emotion.NEUTRAL)

    def set_emotion(self, emotion: Emotion | str):
        """Set active baseline emotional expression without resetting other subsystems."""
        if isinstance(emotion, str):
            clean = emotion.lower().strip()
            matched = Emotion.NEUTRAL
            for e in Emotion:
                if e.value == clean:
                    matched = e
                    break
            emotion = matched

        if self.state.emotion != emotion:
            self.state.emotion = emotion
            self._update_face()

    def set_speaking(self, speaking: bool):
        """Signal speaking turn start/stop."""
        self.state.speaking = speaking
        if not speaking:
            self.lipsync.reset()

    def set_state(self, op_state: OperationalState | str):
        """Update overall operational mode."""
        if isinstance(op_state, str):
            clean = op_state.lower().strip()
            matched = OperationalState.IDLE
            for s in OperationalState:
                if s.value == clean:
                    matched = s
                    break
            op_state = matched

        self.state.operational_state = op_state
        self.state.speaking = (op_state == OperationalState.SPEAKING)
        self.state.listening = (op_state == OperationalState.LISTENING)
        self.state.thinking = (op_state == OperationalState.THINKING)

        if op_state == OperationalState.THINKING:
            self.set_emotion(Emotion.THINKING)
        elif op_state in (OperationalState.IDLE, OperationalState.STANDBY):
            self.set_emotion(Emotion.NEUTRAL)
            self.lipsync.reset()

    def process_audio_chunk(self, pcm_bytes: bytes):
        """Forward live audio chunk to LipSyncController."""
        self.lipsync.process_audio(pcm_bytes)

    def reset_to_idle(self):
        """Reset avatar state cleanly to idle neutral."""
        self.state.speaking = False
        self.state.thinking = False
        self.state.listening = False
        self.state.operational_state = OperationalState.IDLE
        self.set_emotion(Emotion.NEUTRAL)
        self.gaze.return_to_center()
        self.lipsync.reset()

    def _update_face(self):
        """Trigger base face repaint/update on the presentation widget."""
        if self.avatar and hasattr(self.avatar, "update_face_layer"):
            pixmap = self.assets.get_face_pixmap(self.state.emotion, self.state.blinking, self.state.gaze)
            self.avatar.update_face_layer(pixmap)
        self.face_updated.emit()

    def _update_mouth(self):
        """Trigger mouth overlay repaint/update on the presentation widget."""
        if self.avatar and hasattr(self.avatar, "update_mouth_layer"):
            mouth_pixmap = self.assets.get_mouth_pixmap(self.state.mouth)
            self.avatar.update_mouth_layer(mouth_pixmap)
        self.mouth_updated.emit()
