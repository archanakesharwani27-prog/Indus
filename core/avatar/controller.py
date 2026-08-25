# core/avatar/controller.py
"""
INDUS Avatar System -- Central Avatar Controller
Master orchestrator integrating Gaze, Blink, LipSync, Emotion, and FX subsystems.
Exposes simple, high-level, decoupled public API for the INDUS Brain, UI, and Live Audio Streams.
"""

import time
from typing import Optional, Tuple
from core.avatar.models import (
    AvatarState, EmotionType, GazeDirection, OperationalState, MouthShape
)
from core.avatar.gaze import GazeController
from core.avatar.blink import BlinkController
from core.avatar.lipsync import LipSyncController, LipSyncConfig, VisemeLipSyncProvider
from core.avatar.viseme import VisemeTimeline, text_to_viseme_frames
from core.avatar.emoji_emotion import detect_emotion_from_text, strip_emojis
from core.avatar.models import VisemeShape
from core.avatar.emotion import EmotionController
from core.avatar.fx import AvatarFXController
from core.avatar.events import emit_avatar_event, AvatarEvents


class AvatarController:
    """
    Main Avatar controller managing real-time biological animations and state transitions.
    """

    def __init__(self, config: Optional[LipSyncConfig] = None):
        self.state = AvatarState()
        self.gaze = GazeController()
        self.blink = BlinkController()
        # Viseme-driven lip sync with RMS fallback
        self._viseme_timeline = VisemeTimeline()
        self._viseme_provider = VisemeLipSyncProvider(config=config)
        self._viseme_provider.set_timeline(self._viseme_timeline)
        self.lipsync = LipSyncController(
            provider=self._viseme_provider,
            config=config
        )
        self.emotion = EmotionController()
        self.fx = AvatarFXController()
        self._last_time = time.time()

    # -- Public Behavior API --------------------------------------------------

    def set_emotion(self, emotion: EmotionType | str):
        """Set facial baseline expression (e.g. 'happy', 'thinking', 'sad', 'surprised')."""
        self.emotion.set_emotion(emotion)
        self.state.target_emotion = self.emotion.target_emotion
        emit_avatar_event(AvatarEvents.EMOTION_CHANGED, {"emotion": str(emotion)})

    def set_state(self, state: OperationalState | str):
        """Set operational state (e.g. 'listening', 'thinking', 'speaking', 'standby')."""
        if isinstance(state, str):
            clean = state.lower().strip()
            matched = OperationalState.IDLE
            for s in OperationalState:
                if s.value == clean:
                    matched = s
                    break
            state = matched

        self.state.operational_state = state
        self.state.speaking = (state == OperationalState.SPEAKING)
        self.state.listening = (state == OperationalState.LISTENING)
        self.state.thinking = (state == OperationalState.THINKING)

        if state == OperationalState.THINKING:
            self.set_emotion(EmotionType.THINKING)
        elif state == OperationalState.SPEAKING:
            self.lipsync.is_speaking = True
        elif state in (OperationalState.IDLE, OperationalState.STANDBY):
            self.lipsync.stop_speech()
            self.set_emotion(EmotionType.NEUTRAL)

        # State color mappings
        color_map = {
            OperationalState.LISTENING:  "#00FFFF",
            OperationalState.SPEAKING:   "#00BFFF",
            OperationalState.THINKING:   "#FFB300",
            OperationalState.PROCESSING: "#FFB300",
            OperationalState.MUTED:      "#FF2244",
            OperationalState.ERROR:      "#FF2244",
            OperationalState.WARNING:    "#FFB300",
            OperationalState.SUCCESS:    "#00FF88",
            OperationalState.STANDBY:    "#00FFFF",
            OperationalState.IDLE:       "#00FFFF",
        }
        self.state.hud_ring_color = color_map.get(state, "#00FFFF")
        emit_avatar_event(AvatarEvents.STATE_CHANGED, {"state": str(state.value)})

    def look_at(self, x: float, y: float):
        """Set continuous normalized gaze coordinate target (-1.0 to 1.0)."""
        self.gaze.look_at(x, y)

    def look_direction(self, direction: GazeDirection):
        """Set one of 9 discrete cardinal/diagonal gaze directions."""
        self.gaze.look_direction(direction)

    def look_left(self):
        self.look_direction(GazeDirection.LEFT)

    def look_right(self):
        self.look_direction(GazeDirection.RIGHT)

    def look_center(self):
        self.gaze.return_to_center()

    def follow_cursor(self, screen_x: float, screen_y: float, screen_w: float, screen_h: float):
        """Direct eye gaze toward user's cursor / target on screen."""
        self.gaze.follow_cursor(screen_x, screen_y, screen_w, screen_h)

    def set_cursor_tracking(self, enabled: bool):
        """Enable or disable cursor following."""
        self.state.cursor_tracking_enabled = enabled
        self.gaze.set_cursor_tracking(enabled)

    def look_at_vision_target(self, x: float, y: float, w: float, h: float, screen_w: float = 1920, screen_h: float = 1080):
        """Direct eye gaze toward detected vision bounding box."""
        target_center_x = x + w / 2.0
        target_center_y = y + h / 2.0
        self.follow_cursor(target_center_x, target_center_y, screen_w, screen_h)
        emit_avatar_event(AvatarEvents.VISION_TARGET_CHANGED, {"bbox": [x, y, w, h]})

    def start_blink(self):
        """Trigger an instant natural blink."""
        self.blink.trigger_blink()

    def start_speaking(self):
        """Signal start of audio speech output."""
        self.set_state(OperationalState.SPEAKING)
        self.lipsync.is_speaking = True
        emit_avatar_event(AvatarEvents.SPEECH_STARTED)

    def stop_speaking(self):
        """Signal end of audio speech output (triggers smooth mouth closure)."""
        self.lipsync.stop_speech()
        self.state.speaking = False
        if self.state.operational_state == OperationalState.SPEAKING:
            self.set_state(OperationalState.LISTENING)
        emit_avatar_event(AvatarEvents.SPEECH_FINISHED)

    def process_audio_chunk(self, pcm_bytes: bytes):
        """Ingest live PCM audio chunk from Gemini Live/TTS and compute real-time lip sync."""
        if not pcm_bytes:
            return
        openness = self.lipsync.process_chunk(pcm_bytes)
        self.state.mouth_openness = openness
        self.state.mouth_shape = self.lipsync.current_shape
        self.state.current_rms = getattr(self.lipsync.provider, "last_rms", 0.0)
        self.state.audio_level = min(1.0, self.state.current_rms / 3000.0)

    def set_listening(self, is_listening: bool):
        """Switch to listening operational mode."""
        self.set_state(OperationalState.LISTENING if is_listening else OperationalState.IDLE)

    def set_thinking(self, is_thinking: bool):
        """Switch to thinking operational mode."""
        self.set_state(OperationalState.THINKING if is_thinking else OperationalState.IDLE)

    def reset_to_idle(self):
        """Reset gaze, emotion, and mouth smoothly to default idle state."""
        self.set_emotion(EmotionType.NEUTRAL)
        self.set_state(OperationalState.IDLE)
        self.look_center()
        self.stop_speaking()
        self.reset_viseme()

    # -- Viseme + Emoji Emotion API -------------------------------------------

    def feed_speech_text(self, text: str, speech_rate: float = 1.0):
        """
        Convert text to viseme frames and queue for playback.
        Call whenever INDUS output transcription chunk arrives.
        Streaming-safe: appends if timeline already active.
        """
        if not text or not text.strip():
            return
        try:
            clean = strip_emojis(text)
            frames = text_to_viseme_frames(clean, speech_rate=speech_rate)
            if not frames:
                return
            if self._viseme_timeline.is_active:
                self._viseme_timeline.append(frames)
            else:
                self._viseme_timeline.load(frames)
        except Exception as e:
            print(f"[Avatar] feed_speech_text error: {e}")

    def detect_and_set_emotion(self, text: str):
        """
        Parse emojis + keywords from Gemini output → update face expression.
        Call whenever any output transcription arrives.
        """
        try:
            emotion = detect_emotion_from_text(text)
            if emotion is not None:
                self.set_emotion(emotion)
        except Exception as e:
            print(f"[Avatar] detect_and_set_emotion error: {e}")

    def reset_viseme(self):
        """Clear viseme timeline. Call on turn_complete / stop_speaking."""
        self._viseme_timeline.reset()

    # -- 60 FPS Physics Step --------------------------------------------------

    def update(self, dt: Optional[float] = None) -> AvatarState:
        """
        Step all sub-controller physics loops and return current AvatarState.
        Designed to be called every 16ms (60 FPS) by QTimer or with custom simulation dt.
        """
        now = time.time()
        if dt is None:
            dt = max(0.005, min(0.1, now - self._last_time))
            self._last_time = now

        if not self.state.animation_enabled:
            return self.state

        # 1. Step Emotion
        self.emotion.update(dt)
        self.state.current_emotion = self.emotion.current_emotion
        self.state.emotion_blend_progress = self.emotion.blend_progress
        self.state.mouth_smile_curve = self.emotion.mouth_smile_curve  # Sync to AvatarState

        # 2. Step Gaze
        gaze_x, gaze_y = self.gaze.update(
            dt,
            is_thinking=self.state.thinking,
            is_speaking=self.state.speaking
        )
        self.state.gaze_x = gaze_x
        self.state.gaze_y = gaze_y
        self.state.gaze_direction = self.gaze.current_direction

        # 3. Step Blink (preserves gaze)
        coverage = self.blink.update(dt, blink_rate_multiplier=self.emotion.blink_interval_factor)
        self.state.eyelid_coverage = coverage
        self.state.blink_state = self.blink.state

        # 4. Step LipSync (viseme-driven + RMS fallback)
        openness = self.lipsync.update(dt)
        if self.state.speaking or self.state.audio_level > 0.02:
            # Dynamically boost mouth opening with live speech audio energy
            audio_openness = min(1.0, self.state.audio_level * 1.35)
            voice_openness = max(openness, audio_openness)
        else:
            voice_openness = openness

        # Blend emotional baseline opening with voice openness
        self.state.mouth_openness = max(voice_openness, self.emotion.mouth_baseline_open)
        self.state.mouth_shape = self.lipsync.current_shape

        # Sync current viseme shape to AvatarState for renderer
        prov = self._viseme_provider
        if prov.current_viseme is not None:
            self.state.viseme_shape = prov.current_viseme
        elif self.state.mouth_openness < 0.05:
            self.state.viseme_shape = VisemeShape.SILENCE

        # 5. Step FX
        self.fx.update(dt, self.state.operational_state, self.state.audio_level)
        self.state.magenta_ring_pulse = self.fx.pulse
        self.state.last_update_time = now

        return self.state
