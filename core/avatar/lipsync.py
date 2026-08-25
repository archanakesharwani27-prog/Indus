# core/avatar/lipsync.py
"""
INDUS Avatar System -- Voice-Driven Lip-Sync Controller
Transforms live audio stream energy into smooth, natural mouth movements
with attack/decay filtering and emotional baseline co-existence.
"""

from abc import ABC, abstractmethod
from typing import Optional
from core.avatar.models import MouthShape, LipSyncConfig
from core.avatar.transitions import clamp, apply_envelope
from core.avatar.audio import compute_pcm_rms


class LipSyncProvider(ABC):
    """Abstract interface for modular lip-sync algorithms (RMS, Phonemes, Visemes)."""
    @abstractmethod
    def process_audio(self, pcm_bytes: bytes) -> float:
        """Returns normalized mouth aperture between 0.0 (closed) and 1.0 (wide)."""
        pass


class RMSLipSyncProvider(LipSyncProvider):
    """
    Real-time energy-based lip-sync with noise gating and dynamic normalization.
    """

    def __init__(self, config: Optional[LipSyncConfig] = None):
        self.config = config or LipSyncConfig()
        self.current_openness = 0.0
        self.last_rms = 0.0

    def process_audio(self, pcm_bytes: bytes) -> float:
        rms = compute_pcm_rms(pcm_bytes)
        self.last_rms = rms

        # 1. Noise gate subtraction
        if rms < self.config.noise_gate_rms:
            target_openness = 0.0
        elif rms < self.config.slight_threshold:
            # Range: 0.0 to 0.35 (slight opening)
            ratio = (rms - self.config.noise_gate_rms) / max(1.0, (self.config.slight_threshold - self.config.noise_gate_rms))
            target_openness = ratio * 0.35
        elif rms < self.config.medium_threshold:
            # Range: 0.35 to 0.70 (medium opening)
            ratio = (rms - self.config.slight_threshold) / max(1.0, (self.config.medium_threshold - self.config.slight_threshold))
            target_openness = 0.35 + ratio * 0.35
        else:
            # Range: 0.70 to 1.00 (wide opening)
            ratio = (rms - self.config.medium_threshold) / max(1.0, (self.config.wide_threshold - self.config.medium_threshold))
            target_openness = 0.70 + clamp(ratio, 0.0, 1.0) * 0.30

        # 2. Apply responsive attack & smooth decay envelope
        self.current_openness = apply_envelope(
            self.current_openness,
            target_openness,
            attack=self.config.attack_factor,
            decay=self.config.decay_factor,
        )

        return self.current_openness


class LipSyncController:
    """
    Orchestrates voice lip-sync, mouth shape classification, and smooth closure.
    """

    def __init__(self, provider: Optional[LipSyncProvider] = None, config: Optional[LipSyncConfig] = None):
        self.config = config or LipSyncConfig()
        self.provider = provider or RMSLipSyncProvider(self.config)
        self.openness = 0.0
        self.current_shape = MouthShape.CLOSED
        self.is_speaking = False

    def process_chunk(self, pcm_bytes: bytes) -> float:
        """Ingest incoming audio PCM chunk and update mouth aperture."""
        if not self.is_speaking:
            self.is_speaking = True

        raw_openness = self.provider.process_audio(pcm_bytes)
        self.openness = clamp(raw_openness, 0.0, 1.0)
        self._classify_shape()
        return self.openness

    def stop_speech(self):
        """Signals end of speech turn and initiates smooth mouth closure."""
        self.is_speaking = False

    def update(self, dt: float) -> float:
        """
        Step physics: smoothly decay mouth aperture toward 0.0 when speech ends.
        """
        if not self.is_speaking:
            # Smooth natural mouth closing decay
            self.openness = apply_envelope(self.openness, 0.0, attack=0.3, decay=self.config.decay_factor * 1.5)
            if self.openness < 0.02:
                self.openness = 0.0
            self._classify_shape()

        return self.openness

    def _classify_shape(self):
        """Map continuous aperture to discrete mouth shape enum."""
        if self.openness < 0.08:
            self.current_shape = MouthShape.CLOSED
        elif self.openness < 0.38:
            self.current_shape = MouthShape.SLIGHT
        elif self.openness < 0.72:
            self.current_shape = MouthShape.MEDIUM
        else:
            self.current_shape = MouthShape.WIDE


class VisemeLipSyncProvider(LipSyncProvider):
    """
    Text-driven lip sync using phoneme viseme timeline.
    Falls back to RMS energy when no timeline is active.
    """

    def __init__(self, config=None):
        from core.avatar.audio import compute_pcm_rms as _crms
        self._compute_rms = _crms
        self._rms_provider = RMSLipSyncProvider(config)
        self._timeline = None      # VisemeTimeline injected by controller
        self._last_time = None
        self._last_dt_ms = 16.0   # default ~60fps
        self._current_viseme = None
        self._current_openness = 0.0
        self._current_spread = 0.0
        self.last_rms = 0.0

    def set_timeline(self, timeline):
        """Inject VisemeTimeline reference from AvatarController."""
        self._timeline = timeline

    def process_audio(self, pcm_bytes: bytes) -> float:
        """
        Advance viseme timeline if active, else fall back to RMS.
        Always computes RMS for audio_level visualizer.
        """
        import time
        now = time.time()
        if self._last_time is not None:
            self._last_dt_ms = max(1.0, (now - self._last_time) * 1000.0)
        self._last_time = now

        # Always compute RMS (used for HUD waveform + audio_level)
        try:
            self.last_rms = self._compute_rms(pcm_bytes)
        except Exception:
            self.last_rms = 0.0

        # ── Viseme timeline active → use it ─────────────────────────────
        if self._timeline is not None and self._timeline.is_active:
            vsm, openness, spread = self._timeline.advance(self._last_dt_ms)
            self._current_viseme = vsm
            self._current_openness = openness
            self._current_spread = spread
            return openness

        # ── RMS fallback ─────────────────────────────────────────────────
        self._current_viseme = None
        self._current_openness = 0.0
        self._current_spread = 0.0
        return self._rms_provider.process_audio(pcm_bytes)

    @property
    def current_viseme(self):
        return self._current_viseme

    @property
    def current_spread(self) -> float:
        return self._current_spread
