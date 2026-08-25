# core/avatar/gaze.py
"""
INDUS Avatar System -- Gaze Controller
Handles 9 discrete eye directions, continuous normalized target tracking (-1.0 to 1.0),
smooth easing, anatomical eye boundary clamping, micro-saccades, and idle/thinking wandering.
"""

import math
import random
import time
from typing import Optional, Tuple
from core.avatar.models import GazeDirection, GazeTarget, AvatarState
from core.avatar.transitions import clamp, lerp, clamp_gaze_radius, ease_in_out_cubic


# Cardinal & diagonal direction vectors (normalized x, y)
DIRECTION_VECTORS = {
    GazeDirection.CENTER:     ( 0.00,  0.00),
    GazeDirection.LEFT:       (-0.85,  0.00),
    GazeDirection.RIGHT:      ( 0.85,  0.00),
    GazeDirection.UP:         ( 0.00, -0.65),
    GazeDirection.DOWN:       ( 0.00,  0.65),
    GazeDirection.UP_LEFT:    (-0.65, -0.50),
    GazeDirection.UP_RIGHT:   ( 0.65, -0.50),
    GazeDirection.DOWN_LEFT:  (-0.65,  0.50),
    GazeDirection.DOWN_RIGHT: ( 0.65,  0.50),
}


class GazeController:
    """
    Manages eye gaze targets, smoothing, cursor following, and micro-saccades.
    """

    def __init__(self, tracking_speed: float = 6.0, micro_gaze_enabled: bool = True):
        self.tracking_speed = tracking_speed
        self.micro_gaze_enabled = micro_gaze_enabled
        self.cursor_tracking_enabled = True

        # Coordinates
        self.current_x = 0.0
        self.current_y = 0.0
        self.target_x = 0.0
        self.target_y = 0.0
        self.current_direction = GazeDirection.CENTER

        # Micro-saccades timing
        self._last_micro_shift = time.time()
        self._next_micro_interval = random.uniform(2.0, 4.5)
        self._micro_offset_x = 0.0
        self._micro_offset_y = 0.0

        # Thinking state gaze wander timing
        self._thinking_phase = 0.0

        # Active target
        self._active_target: Optional[GazeTarget] = None

    def look_direction(self, direction: GazeDirection):
        """Set gaze to one of 9 discrete cardinal/diagonal directions."""
        vec = DIRECTION_VECTORS.get(direction, (0.0, 0.0))
        self.look_at(vec[0], vec[1], label=direction.value, priority=2)
        self.current_direction = direction

    def look_at(self, x: float, y: float, label: str = "custom", priority: int = 2):
        """Set explicit normalized target coordinate (-1.0 to 1.0)."""
        clamped_x, clamped_y = clamp_gaze_radius(x, y)
        self.target_x = clamped_x
        self.target_y = clamped_y
        self._active_target = GazeTarget(x=clamped_x, y=clamped_y, is_tracking=True, priority=priority, label=label)
        self._determine_direction(clamped_x, clamped_y)

    def follow_cursor(self, screen_x: float, screen_y: float, screen_w: float, screen_h: float):
        """Map screen pixel coordinate to avatar-relative normalized gaze target (-1.0 to 1.0)."""
        if not self.cursor_tracking_enabled:
            return
        if screen_w <= 0 or screen_h <= 0:
            return

        # Normalized -1.0 to 1.0 from center of screen/widget
        norm_x = clamp(((screen_x / screen_w) - 0.5) * 2.0, -1.0, 1.0)
        norm_y = clamp(((screen_y / screen_h) - 0.5) * 2.0, -1.0, 1.0)
        self.look_at(norm_x * 0.85, norm_y * 0.70, label="cursor", priority=3)

    def return_to_center(self):
        """Smoothly reset gaze back to center."""
        self.look_at(0.0, 0.0, label="center", priority=0)
        self.current_direction = GazeDirection.CENTER

    def set_cursor_tracking(self, enabled: bool):
        """Enable or disable cursor following."""
        self.cursor_tracking_enabled = enabled
        if not enabled and self._active_target and self._active_target.label == "cursor":
            self.return_to_center()

    def update(self, dt: float, is_thinking: bool = False, is_speaking: bool = False) -> Tuple[float, float]:
        """
        Step gaze physics: smooth interpolation toward target + micro movements.
        Returns (current_x, current_y).
        """
        now = time.time()

        # Handle micro-saccades / natural wandering if not actively tracking high-priority target
        has_high_priority = self._active_target and self._active_target.priority >= 3
        if not has_high_priority and self.micro_gaze_enabled:
            if is_thinking:
                # Thinking gaze: slower upward-left or upward-right wandering
                self._thinking_phase += dt * 1.5
                self._micro_offset_x = 0.45 * math.sin(self._thinking_phase)
                self._micro_offset_y = -0.35 + 0.15 * math.cos(self._thinking_phase * 0.7)
            elif is_speaking:
                # Speaking gaze: small natural conversational eye gestures
                if now - self._last_micro_shift > self._next_micro_interval:
                    self._last_micro_shift = now
                    self._next_micro_interval = random.uniform(2.5, 5.0)
                    self._micro_offset_x = random.uniform(-0.15, 0.15)
                    self._micro_offset_y = random.uniform(-0.10, 0.10)
            else:
                # Idle state: occasional subtle gaze shifts, returning toward center
                if now - self._last_micro_shift > self._next_micro_interval:
                    self._last_micro_shift = now
                    self._next_micro_interval = random.uniform(3.0, 6.0)
                    if random.random() < 0.60:
                        # 60% chance return to center
                        self._micro_offset_x = 0.0
                        self._micro_offset_y = 0.0
                    else:
                        # 40% chance subtle micro glance
                        self._micro_offset_x = random.uniform(-0.35, 0.35)
                        self._micro_offset_y = random.uniform(-0.25, 0.25)
        else:
            self._micro_offset_x = 0.0
            self._micro_offset_y = 0.0

        # Combine base target with micro-offset
        effective_target_x, effective_target_y = clamp_gaze_radius(
            self.target_x + self._micro_offset_x,
            self.target_y + self._micro_offset_y
        )

        # Smooth exponential interpolation (framerate-independent)
        blend = 1.0 - math.exp(-self.tracking_speed * dt)
        self.current_x = lerp(self.current_x, effective_target_x, blend)
        self.current_y = lerp(self.current_y, effective_target_y, blend)

        return (self.current_x, self.current_y)

    def _determine_direction(self, x: float, y: float):
        """Map continuous coordinate to closest discrete direction enum."""
        dist = math.sqrt(x * x + y * y)
        if dist < 0.25:
            self.current_direction = GazeDirection.CENTER
            return

        angle_deg = math.degrees(math.atan2(y, x)) % 360  # 0=Right, 90=Down, 180=Left, 270=Up
        if 337.5 <= angle_deg or angle_deg < 22.5:
            self.current_direction = GazeDirection.RIGHT
        elif 22.5 <= angle_deg < 67.5:
            self.current_direction = GazeDirection.DOWN_RIGHT
        elif 67.5 <= angle_deg < 112.5:
            self.current_direction = GazeDirection.DOWN
        elif 112.5 <= angle_deg < 157.5:
            self.current_direction = GazeDirection.DOWN_LEFT
        elif 157.5 <= angle_deg < 202.5:
            self.current_direction = GazeDirection.LEFT
        elif 202.5 <= angle_deg < 247.5:
            self.current_direction = GazeDirection.UP_LEFT
        elif 247.5 <= angle_deg < 292.5:
            self.current_direction = GazeDirection.UP
        else:
            self.current_direction = GazeDirection.UP_RIGHT
