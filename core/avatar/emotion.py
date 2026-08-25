# core/avatar/emotion.py
"""
INDUS Avatar System -- Emotion Controller
Manages baseline facial expression profiles, transition speeds, eyebrow/eye openness modifiers,
and enables seamless co-existence between emotional baselines (e.g. smile/frown) and dynamic voice lip-sync.
"""

from typing import Dict, Optional, Tuple
from core.avatar.models import EmotionType, EmotionProfile, AvatarState
from core.avatar.transitions import lerp, ease_in_out_cubic, clamp


# 10 comprehensive emotion profiles
EMOTION_PROFILES: Dict[EmotionType, EmotionProfile] = {
    EmotionType.NEUTRAL: EmotionProfile(
        emotion=EmotionType.NEUTRAL,
        eyebrow_raise=0.0,
        eye_openness=1.0,
        mouth_smile_curve=0.0,
        mouth_baseline_open=0.0,
        gaze_tendency_y=0.0,
        blink_interval_factor=1.0,
        pulse_color_hex="#00FFFF",
        transition_speed=3.0,
    ),
    EmotionType.HAPPY: EmotionProfile(
        emotion=EmotionType.HAPPY,
        eyebrow_raise=0.25,
        eye_openness=0.92,        # gentle smiling squint
        mouth_smile_curve=0.85,   # broad smile curve
        mouth_baseline_open=0.05,
        gaze_tendency_y=0.0,
        blink_interval_factor=1.1,
        pulse_color_hex="#00FFFF",
        transition_speed=3.5,
    ),
    EmotionType.SAD: EmotionProfile(
        emotion=EmotionType.SAD,
        eyebrow_raise=-0.35,      # slight inner brow raise / outer drop
        eye_openness=0.80,        # heavy eyelids
        mouth_smile_curve=-0.75,  # down-turned mouth curve
        mouth_baseline_open=0.0,
        gaze_tendency_y=0.25,     # looking down
        blink_interval_factor=1.6,# slower blinks
        pulse_color_hex="#008A8A",
        transition_speed=2.0,
    ),
    EmotionType.THINKING: EmotionProfile(
        emotion=EmotionType.THINKING,
        eyebrow_raise=0.15,
        eye_openness=0.95,
        mouth_smile_curve=-0.10,  # slight pursed lips
        mouth_baseline_open=0.0,
        gaze_tendency_y=-0.35,    # looking upward
        blink_interval_factor=0.85,
        pulse_color_hex="#FFB300",# amber pulse
        transition_speed=2.5,
    ),
    EmotionType.SURPRISED: EmotionProfile(
        emotion=EmotionType.SURPRISED,
        eyebrow_raise=0.85,       # high raised brows
        eye_openness=1.25,        # wide open eyes
        mouth_smile_curve=0.10,
        mouth_baseline_open=0.35, # round open O-mouth baseline
        gaze_tendency_y=-0.10,
        blink_interval_factor=0.6,# rapid blinks
        pulse_color_hex="#00BFFF",
        transition_speed=5.0,
    ),
    EmotionType.ANGRY: EmotionProfile(
        emotion=EmotionType.ANGRY,
        eyebrow_raise=-0.80,      # strongly furrowed V-brows
        eye_openness=0.88,
        mouth_smile_curve=-0.65,  # firm tense frown
        mouth_baseline_open=0.0,
        gaze_tendency_y=0.10,
        blink_interval_factor=1.4,
        pulse_color_hex="#FF2244",# alert red pulse
        transition_speed=4.0,
    ),
    EmotionType.CONFUSED: EmotionProfile(
        emotion=EmotionType.CONFUSED,
        eyebrow_raise=-0.20,      # asymmetric head/brow tilt
        eye_openness=0.90,
        mouth_smile_curve=-0.25,
        mouth_baseline_open=0.05,
        gaze_tendency_y=-0.20,
        blink_interval_factor=1.0,
        pulse_color_hex="#FFB300",
        transition_speed=3.0,
    ),
    EmotionType.CONCERNED: EmotionProfile(
        emotion=EmotionType.CONCERNED,
        eyebrow_raise=0.30,
        eye_openness=0.95,
        mouth_smile_curve=-0.40,
        mouth_baseline_open=0.0,
        gaze_tendency_y=0.05,
        blink_interval_factor=0.9,
        pulse_color_hex="#FF8800",
        transition_speed=3.0,
    ),
    EmotionType.CALM: EmotionProfile(
        emotion=EmotionType.CALM,
        eyebrow_raise=0.05,
        eye_openness=0.90,
        mouth_smile_curve=0.20,
        mouth_baseline_open=0.0,
        gaze_tendency_y=0.0,
        blink_interval_factor=1.3,
        pulse_color_hex="#00E5FF",
        transition_speed=2.0,
    ),
    EmotionType.EXCITED: EmotionProfile(
        emotion=EmotionType.EXCITED,
        eyebrow_raise=0.50,
        eye_openness=1.15,
        mouth_smile_curve=0.90,
        mouth_baseline_open=0.15,
        gaze_tendency_y=-0.10,
        blink_interval_factor=0.75,
        pulse_color_hex="#00FFFF",
        transition_speed=4.5,
    ),
}


class EmotionController:
    """
    Manages emotional state blending and provides interpolated facial modifier parameters.
    """

    def __init__(self, initial_emotion: EmotionType = EmotionType.NEUTRAL):
        self.current_emotion = initial_emotion
        self.target_emotion = initial_emotion
        self.blend_progress = 1.0  # 1.0 = fully transitioned

        self._current_profile = EMOTION_PROFILES.get(initial_emotion, EMOTION_PROFILES[EmotionType.NEUTRAL])
        self._target_profile = self._current_profile

        # Active blended parameters
        self.eyebrow_raise = self._current_profile.eyebrow_raise
        self.eye_openness = self._current_profile.eye_openness
        self.mouth_smile_curve = self._current_profile.mouth_smile_curve
        self.mouth_baseline_open = self._current_profile.mouth_baseline_open
        self.gaze_tendency_y = self._current_profile.gaze_tendency_y
        self.blink_interval_factor = self._current_profile.blink_interval_factor
        self.pulse_color = self._current_profile.pulse_color_hex

    def set_emotion(self, emotion: EmotionType | str):
        """Set new target emotion with smooth transition curve."""
        if isinstance(emotion, str):
            clean_str = emotion.lower().strip()
            # Find matching enum
            matched = EmotionType.NEUTRAL
            for e in EmotionType:
                if e.value == clean_str:
                    matched = e
                    break
            emotion = matched

        if emotion == self.target_emotion and self.blend_progress >= 1.0:
            return

        # Snapshot current interpolated values as new start point
        self.current_emotion = self.target_emotion
        self._current_profile = self._target_profile
        self.target_emotion = emotion
        self._target_profile = EMOTION_PROFILES.get(emotion, EMOTION_PROFILES[EmotionType.NEUTRAL])
        self.blend_progress = 0.0

    def update(self, dt: float):
        """Step emotion interpolation physics."""
        if self.blend_progress < 1.0:
            speed = self._target_profile.transition_speed
            self.blend_progress = clamp(self.blend_progress + dt * speed, 0.0, 1.0)
            t = ease_in_out_cubic(self.blend_progress)

            self.eyebrow_raise = lerp(self._current_profile.eyebrow_raise, self._target_profile.eyebrow_raise, t)
            self.eye_openness = lerp(self._current_profile.eye_openness, self._target_profile.eye_openness, t)
            self.mouth_smile_curve = lerp(self._current_profile.mouth_smile_curve, self._target_profile.mouth_smile_curve, t)
            self.mouth_baseline_open = lerp(self._current_profile.mouth_baseline_open, self._target_profile.mouth_baseline_open, t)
            self.gaze_tendency_y = lerp(self._current_profile.gaze_tendency_y, self._target_profile.gaze_tendency_y, t)
            self.blink_interval_factor = lerp(self._current_profile.blink_interval_factor, self._target_profile.blink_interval_factor, t)
            self.pulse_color = self._target_profile.pulse_color_hex

            if self.blend_progress >= 1.0:
                self.current_emotion = self.target_emotion
        else:
            self.current_emotion = self.target_emotion
            self.eyebrow_raise = self._target_profile.eyebrow_raise
            self.eye_openness = self._target_profile.eye_openness
            self.mouth_smile_curve = self._target_profile.mouth_smile_curve
            self.mouth_baseline_open = self._target_profile.mouth_baseline_open
            self.gaze_tendency_y = self._target_profile.gaze_tendency_y
            self.blink_interval_factor = self._target_profile.blink_interval_factor
            self.pulse_color = self._target_profile.pulse_color_hex
