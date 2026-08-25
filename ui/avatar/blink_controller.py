# ui/avatar/blink_controller.py
"""
INDUS Avatar System -- Randomized Biological Blink Controller
Interval: 3.5 - 6.5 seconds
Duration: 180 - 200 ms
Preserves active gaze and emotion without resetting other states.
"""

import random
from typing import Any
from PyQt6.QtCore import QTimer


class BlinkController:
    """
    Manages non-blocking natural blinking cycles using randomized single-shot QTimers.
    """

    def __init__(self, face_manager: Any):
        self.manager = face_manager
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._blink)
        self.is_active = True
        self._schedule()

    def _schedule(self):
        if not self.is_active:
            return
        delay = random.randint(3500, 6500)
        self.timer.start(delay)

    def _blink(self):
        if not self.is_active:
            return
        self.manager.state.blinking = True
        self.manager._update_face()

        # Hold closed for 180-200ms
        duration = random.randint(180, 200)
        QTimer.singleShot(duration, self._finish)

    def _finish(self):
        self.manager.state.blinking = False
        self.manager._update_face()
        self._schedule()

    def trigger_now(self):
        """Immediately trigger a blink."""
        self.timer.stop()
        self._blink()

    def stop(self):
        self.is_active = False
        self.timer.stop()
