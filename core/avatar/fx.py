# core/avatar/fx.py
"""
INDUS Avatar System -- Visual FX & Cyberpunk HUD Controller
Drives reactive mechanical ring rotations, equalizer audio bars, particle dynamics,
and state-colored aura glows.
"""

import math
import random
from core.avatar.models import OperationalState, AvatarState
from core.avatar.transitions import lerp, clamp


class AvatarFXController:
    """
    Manages HUD ring rotation angles, particle dynamics, and reactive state glows.
    """

    def __init__(self):
        self.rings = [0.0, 120.0, 240.0]
        self.scan_angle = 0.0
        self.scan_angle2 = 180.0
        self.pulse = 0.0
        self._pulse_dir = 1
        self.particle_count = 22
        self.particles = [
            {
                "ang": random.uniform(0, 360),
                "spd": random.uniform(0.4, 1.2),
                "r":   random.uniform(0.13, 0.24),
                "sz":  random.uniform(1.5, 3.5),
                "a":   random.randint(70, 190),
            }
            for _ in range(self.particle_count)
        ]
        self.magenta_pulse_alpha = 180

    def update(self, dt: float, state: OperationalState, audio_level: float):
        """Step visual FX physics at 60 FPS."""
        # Pulse breathing rate
        pulse_speed = 1.8 if state == OperationalState.SPEAKING else (2.5 if state == OperationalState.THINKING else 1.0)
        self.pulse += dt * pulse_speed * self._pulse_dir
        if self.pulse >= 1.0:
            self.pulse = 1.0
            self._pulse_dir = -1
        elif self.pulse <= 0.0:
            self.pulse = 0.0
            self._pulse_dir = 1

        self.magenta_pulse_alpha = int(180 + 55 * self.pulse)

        # Ring rotations
        boost = 1.0 + audio_level * 2.5
        speed_factor = 2.2 if state == OperationalState.SPEAKING else (1.5 if state == OperationalState.THINKING else 0.7)
        for i in range(3):
            direction = 1 if i % 2 == 0 else -1
            self.rings[i] = (self.rings[i] + direction * speed_factor * boost * (i * 0.4 + 0.6) * dt * 60.0) % 360

        # Scan sweeps
        self.scan_angle = (self.scan_angle + (3.0 if state == OperationalState.SPEAKING else 1.0) * boost * dt * 60.0) % 360
        self.scan_angle2 = (self.scan_angle2 - (2.2 if state == OperationalState.SPEAKING else 0.6) * boost * dt * 60.0) % 360

        # Particles drift
        for p in self.particles:
            p["ang"] = (p["ang"] + p["spd"] * (1.0 + audio_level * 1.5) * dt * 60.0) % 360
