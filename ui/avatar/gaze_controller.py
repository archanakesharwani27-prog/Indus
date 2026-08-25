# ui/avatar/gaze_controller.py
"""
INDUS Avatar System -- State-Dependent Gaze Controller
Subtle eye movements with state-dependent probability distribution:
  NEUTRAL:   center-heavy
  THINKING:  left/right/up frequent wandering
  SPEAKING:  mostly center with micro shifts
  SAD:       downward / center slower shift
  SURPRISED: locked center
"""

import random
from typing import Any, List
from PyQt6.QtCore import QTimer
from ui.avatar.avatar_state import Emotion


class GazeController:
    """
    Coordinates state-dependent natural eye shifts with smooth return-to-center.
    """

    GAZES = ["center", "left", "right", "up", "down"]

    def __init__(self, manager: Any, interval_ms: int = 2200):
        self.manager = manager
        self.timer = QTimer()
        self.timer.timeout.connect(self._shift)
        self.timer.start(interval_ms)

    def _shift(self):
        state = self.manager.state
        current_em = state.emotion

        # State-dependent probability choices
        if current_em == Emotion.THINKING:
            # Thinking: 70% chance to look up/left/right, 30% center
            choices = ["up", "left", "right", "up", "center"]
        elif current_em == Emotion.SAD:
            # Sad: 60% down, 40% center
            choices = ["down", "down", "center", "center"]
        elif current_em == Emotion.SURPRISED:
            # Surprised: locked center
            choices = ["center"]
        elif state.speaking:
            # Speaking: 80% center, 20% slight shift
            choices = ["center", "center", "center", "center", "left", "right"]
        else:
            # Neutral / Idle: 70% center, 30% cardinal shift
            choices = ["center", "center", "center", "center", "left", "right", "up"]

        target_gaze = random.choice(choices)
        if state.gaze != target_gaze:
            state.gaze = target_gaze
            self.manager._update_face()

    def look_at(self, direction: str):
        """Set explicit gaze direction."""
        clean = direction.lower().strip()
        if clean in self.GAZES:
            self.manager.state.gaze = clean
            self.manager._update_face()

    def return_to_center(self):
        """Reset gaze back to center."""
        self.manager.state.gaze = "center"
        self.manager._update_face()

    def stop(self):
        self.timer.stop()
