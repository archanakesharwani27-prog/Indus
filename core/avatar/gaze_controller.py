# core/avatar/gaze_controller.py
"""
INDUS Avatar System -- State-Dependent Gaze Controller
"""

import random
from typing import Any
from PyQt6.QtCore import QTimer
from core.avatar.avatar_state import Emotion


class GazeController:
    GAZES = ["center", "left", "right", "up", "down"]

    def __init__(self, manager: Any, interval_ms: int = 2200):
        self.manager = manager
        self.timer = QTimer()
        self.timer.timeout.connect(self._shift)
        self.timer.start(interval_ms)

    def _shift(self):
        state = self.manager.state
        current_em = state.emotion

        if current_em == Emotion.THINKING:
            choices = ["up", "left", "right", "up", "center"]
        elif current_em == Emotion.SAD:
            choices = ["down", "down", "center", "center"]
        elif current_em == Emotion.SURPRISED:
            choices = ["center"]
        elif state.speaking:
            choices = ["center", "center", "center", "center", "left", "right"]
        else:
            choices = ["center", "center", "center", "center", "left", "right", "up"]

        target_gaze = random.choice(choices)
        if state.gaze != target_gaze:
            state.gaze = target_gaze
            self.manager._update_face()

    def look_at(self, direction: str):
        clean = direction.lower().strip()
        if clean in self.GAZES:
            self.manager.state.gaze = clean
            self.manager._update_face()

    def return_to_center(self):
        self.manager.state.gaze = "center"
        self.manager._update_face()

    def stop(self):
        self.timer.stop()
