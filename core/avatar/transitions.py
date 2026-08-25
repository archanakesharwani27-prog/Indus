# core/avatar/transitions.py
"""
INDUS Avatar System -- Smooth Interpolation & Easing Math
Provides non-linear transitions for gaze, eyelids, emotions, and audio envelopes.
"""

import math
from typing import Tuple


def clamp(value: float, min_val: float = -1.0, max_val: float = 1.0) -> float:
    """Clamp value between min_val and max_val."""
    return max(min_val, min(max_val, value))


def lerp(start: float, end: float, factor: float) -> float:
    """Linear interpolation between start and end."""
    factor = max(0.0, min(1.0, factor))
    return start + (end - start) * factor


def lerp_2d(p1: Tuple[float, float], p2: Tuple[float, float], factor: float) -> Tuple[float, float]:
    """Interpolate between two 2D points."""
    return (lerp(p1[0], p2[0], factor), lerp(p1[1], p2[1], factor))


def ease_in_out_cubic(t: float) -> float:
    """Cubic ease-in-out curve for natural biological gaze & blink acceleration."""
    t = max(0.0, min(1.0, t))
    if t < 0.5:
        return 4.0 * t * t * t
    else:
        p = 2.0 * t - 2.0
        return 0.5 * p * p * p + 1.0


def smooth_step(edge0: float, edge1: float, x: float) -> float:
    """Smooth Hermite interpolation between edge0 and edge1."""
    t = clamp((x - edge0) / (edge1 - edge0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def clamp_gaze_radius(x: float, y: float, max_radius: float = 1.0) -> Tuple[float, float]:
    """Ensure gaze vector does not exceed anatomical elliptical eye socket boundary."""
    # Elliptical constraint: horizontal gaze allows slightly wider range than vertical
    norm_x = x / 1.0
    norm_y = y / 0.75
    dist = math.sqrt(norm_x * norm_x + norm_y * norm_y)
    if dist > max_radius and dist > 0.0001:
        scale = max_radius / dist
        return (x * scale, y * scale)
    return (clamp(x, -max_radius, max_radius), clamp(y, -max_radius * 0.75, max_radius * 0.75))


def apply_envelope(current: float, target: float, attack: float, decay: float) -> float:
    """
    Attack/decay envelope filter.
    When target > current: moves towards target with attack rate.
    When target < current: moves towards target with decay rate.
    """
    if target > current:
        return current + (target - current) * attack
    else:
        return current + (target - current) * decay
