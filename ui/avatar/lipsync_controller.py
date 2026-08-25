# ui/avatar/lipsync_controller.py
"""
INDUS Avatar System -- Voice-Driven LipSync Controller
Asymmetric RMSFilter (attack=0.65, decay=0.25), centralized configurable thresholds,
and 60 FPS UI update throttling.
"""

import math
import struct
import time
from dataclasses import dataclass
from typing import Any, Optional
from ui.avatar.avatar_state import MouthState


@dataclass(frozen=True)
class LipSyncConfig:
    """Authoritative thresholds for voice-driven mouth shape classification."""
    silent_threshold: float = 500.0
    slight_threshold: float = 1800.0
    medium_threshold: float = 3800.0
    target_fps: int = 60


def calculate_rms(pcm_bytes: bytes) -> float:
    """
    Computes Root-Mean-Square (RMS) amplitude energy from raw 16-bit PCM bytes.
    """
    if not pcm_bytes or len(pcm_bytes) < 2:
        return 0.0

    count = len(pcm_bytes) // 2
    format_str = f"<{count}h"
    try:
        samples = struct.unpack(format_str, pcm_bytes[: count * 2])
    except Exception:
        return 0.0

    if not samples:
        return 0.0

    sum_squares = sum(float(s) * float(s) for s in samples)
    return math.sqrt(sum_squares / count)


def classify_mouth(rms: float, config: Optional[LipSyncConfig] = None) -> MouthState:
    """Maps continuous RMS energy to discrete MouthState enum."""
    cfg = config or LipSyncConfig()
    if rms < cfg.silent_threshold:
        return MouthState.BLANK
    if rms < cfg.slight_threshold:
        return MouthState.SLIGHT
    if rms < cfg.medium_threshold:
        return MouthState.MEDIUM
    return MouthState.WIDE


class RMSFilter:
    """
    Asymmetric attack/decay filter: mouth opens quickly, closes smoothly.
    """

    def __init__(self, attack: float = 0.65, decay: float = 0.25):
        self.value = 0.0
        self.attack = attack
        self.decay = decay

    def update(self, target: float) -> float:
        coeff = self.attack if target > self.value else self.decay
        self.value += (target - self.value) * coeff
        return self.value

    def reset(self):
        self.value = 0.0


class LipSyncController:
    """
    Orchestrates real-time audio analysis, filtering, and 60 FPS UI throttling.
    """

    def __init__(self, manager: Any, config: Optional[LipSyncConfig] = None):
        self.manager = manager
        self.config = config or LipSyncConfig()
        self.filter = RMSFilter()

        self.last_ui_update = 0.0
        self.frame_interval = 1.0 / float(self.config.target_fps)

    def process_audio(self, pcm_bytes: bytes) -> MouthState:
        """
        Ingests PCM audio chunk, calculates RMS, applies asymmetric filter,
        and updates avatar mouth shape with 60 FPS UI throttling.
        """
        if not pcm_bytes:
            return self.manager.state.mouth

        raw_rms = calculate_rms(pcm_bytes)
        smoothed_rms = self.filter.update(raw_rms)
        self.manager.state.rms = smoothed_rms

        now = time.perf_counter()
        if now - self.last_ui_update < self.frame_interval:
            return self.manager.state.mouth

        self.last_ui_update = now
        new_mouth = classify_mouth(smoothed_rms, self.config)

        if new_mouth != self.manager.state.mouth:
            self.manager.state.mouth = new_mouth
            self.manager._update_mouth()

        return new_mouth

    def reset(self):
        """Reset mouth overlay immediately to BLANK (e.g. on interruption or turn complete)."""
        self.filter.reset()
        self.manager.state.mouth = MouthState.BLANK
        self.manager.state.rms = 0.0
        self.manager._update_mouth()
