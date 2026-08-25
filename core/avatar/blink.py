# core/avatar/blink.py
"""
INDUS Avatar System -- Blink Controller
Provides randomized biological blinking with natural open/close acceleration curves,
double blinks, thinking blinks, and strict preservation of active gaze direction.
"""

import math
import random
import time
from core.avatar.models import BlinkState, BlinkType
from core.avatar.transitions import ease_in_out_cubic


class BlinkController:
    """
    Manages eyelid closure and opening without changing the active eye gaze coordinates.
    """

    def __init__(
        self,
        min_interval: float = 3.5,
        max_interval: float = 6.5,
        blink_duration: float = 0.20,  # 200ms
    ):
        self.min_interval = min_interval
        self.max_interval = max_interval
        self.blink_duration = blink_duration

        self.state = BlinkState.OPEN
        self.coverage = 0.0          # 0.0 = fully open, 1.0 = fully closed
        self._blink_progress = 0.0   # 0.0 to 1.0 over blink duration
        self._is_blinking = False

        self._last_blink_time = time.time()
        self._next_interval = random.uniform(self.min_interval, self.max_interval)
        self._pending_double_blink = False

    def trigger_blink(self, blink_type: BlinkType = BlinkType.NORMAL):
        """Explicitly trigger a blink sequence."""
        if not self._is_blinking:
            self._is_blinking = True
            self._blink_progress = 0.0
            self.state = BlinkState.CLOSING
            if blink_type == BlinkType.DOUBLE:
                self._pending_double_blink = True

    def update(self, dt: float, blink_rate_multiplier: float = 1.0) -> float:
        """
        Step blink timer and calculate eyelid coverage (0.0 to 1.0).
        """
        now = time.time()

        if self._is_blinking:
            # Advance progress
            self._blink_progress += dt / max(0.05, self.blink_duration)

            if self._blink_progress <= 0.45:
                # Eyelid closing phase (fast acceleration, 45% of duration)
                close_t = self._blink_progress / 0.45
                self.coverage = ease_in_out_cubic(close_t)
                self.state = BlinkState.CLOSING if self.coverage < 0.95 else BlinkState.CLOSED
            elif self._blink_progress <= 1.0:
                # Eyelid opening phase (55% of duration)
                open_t = (self._blink_progress - 0.45) / 0.55
                self.coverage = 1.0 - ease_in_out_cubic(open_t)
                self.state = BlinkState.OPENING if self.coverage > 0.05 else BlinkState.OPEN
            else:
                # Blink completed
                self.coverage = 0.0
                self.state = BlinkState.OPEN
                self._is_blinking = False
                self._last_blink_time = now

                # Double blink check
                if self._pending_double_blink:
                    self._pending_double_blink = False
                    self._next_interval = random.uniform(0.12, 0.25)
                else:
                    self._next_interval = random.uniform(self.min_interval, self.max_interval) / max(0.2, blink_rate_multiplier)

        else:
            # Check if randomized interval elapsed
            elapsed = now - self._last_blink_time
            if elapsed >= self._next_interval:
                # 15% probability of double blink
                is_double = random.random() < 0.15
                self.trigger_blink(BlinkType.DOUBLE if is_double else BlinkType.NORMAL)

        return self.coverage
