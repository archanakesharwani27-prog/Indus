# tests/test_avatar_system.py
"""
INDUS Avatar System -- Comprehensive Automated Test Suite
Verifies both the core physics rendering engine and the controller-driven IndusEmotionFaceManager,
RMSFilter, classify_mouth, parse_emotion_tag, AssetResolver, and 2-layer widget geometry.
"""

import math
import struct
import time
import pytest
from PyQt6.QtWidgets import QApplication
import sys

# Ensure QApplication exists for Qt tests
app = QApplication.instance() or QApplication(sys.argv)

from core.avatar import (
    CoreAvatarState, EmotionType, GazeDirection, BlinkState, BlinkType,
    MouthShape, OperationalState, GazeTarget, CoreLipSyncConfig,
    AvatarController, AvatarRenderer,
    AvatarState, Emotion, MouthState, Gaze, IndusEmotionFaceManager,
    parse_emotion_tag, GazeController, BlinkController,
    LipSyncController, LipSyncConfig, RMSFilter,
    calculate_rms, classify_mouth, AssetResolver, AvatarWidget
)
from core.avatar.audio import compute_pcm_rms
from core.avatar.transitions import clamp, lerp, clamp_gaze_radius, ease_in_out_cubic


class TestAvatarSystem:

    # 1. State initialization
    def test_01_avatar_state_initialization(self):
        ctrl = AvatarController()
        assert ctrl.state.current_emotion == EmotionType.NEUTRAL
        assert ctrl.state.operational_state == OperationalState.IDLE
        assert ctrl.state.gaze_direction == GazeDirection.CENTER
        assert ctrl.state.blink_state == BlinkState.OPEN
        assert ctrl.state.mouth_shape == MouthShape.CLOSED
        assert ctrl.state.speaking is False

    # 2. Emotion transitions
    def test_02_emotion_transitions(self):
        ctrl = AvatarController()
        ctrl.set_emotion(EmotionType.HAPPY)
        assert ctrl.emotion.target_emotion == EmotionType.HAPPY

        for _ in range(30):
            ctrl.update(dt=0.05)
        assert ctrl.emotion.current_emotion == EmotionType.HAPPY
        assert ctrl.emotion.mouth_smile_curve > 0.5

    # 3. Gaze direction changes
    def test_03_gaze_directions(self):
        from core.avatar.gaze import GazeController as CoreGazeController
        gaze = CoreGazeController()
        gaze.look_direction(GazeDirection.LEFT)
        assert gaze.current_direction == GazeDirection.LEFT
        assert gaze.target_x < -0.5

        gaze.look_direction(GazeDirection.UP_RIGHT)
        assert gaze.current_direction == GazeDirection.UP_RIGHT
        assert gaze.target_x > 0.3
        assert gaze.target_y < -0.3

    # 4. Smooth gaze target calculation
    def test_04_smooth_gaze_interpolation(self):
        from core.avatar.gaze import GazeController as CoreGazeController
        gaze = CoreGazeController(tracking_speed=5.0)
        gaze.look_at(0.8, 0.0)

        assert gaze.current_x == 0.0
        x1, _ = gaze.update(0.05)
        assert 0.0 < x1 < 0.8

        for _ in range(20):
            x_final, _ = gaze.update(0.05)
        assert x_final > 0.7

    # 5. Gaze clamping
    def test_05_gaze_clamping(self):
        clamped_x, clamped_y = clamp_gaze_radius(2.5, -3.0, max_radius=1.0)
        assert abs(clamped_x) <= 1.0
        assert abs(clamped_y) <= 0.8

    # 6. Return-to-center behavior
    def test_06_return_to_center(self):
        from core.avatar.gaze import GazeController as CoreGazeController
        gaze = CoreGazeController()
        gaze.look_at(0.9, -0.7)
        gaze.return_to_center()
        assert gaze.target_x == 0.0
        assert gaze.target_y == 0.0
        assert gaze.current_direction == GazeDirection.CENTER

    # 7. Blink timing & state
    def test_07_blink_states(self):
        from core.avatar.blink import BlinkController as CoreBlinkController
        blink = CoreBlinkController(blink_duration=0.20)
        assert blink.state == BlinkState.OPEN

        blink.trigger_blink()
        assert blink.state == BlinkState.CLOSING

        blink.update(0.09)
        assert blink.coverage > 0.8
        assert blink.state in (BlinkState.CLOSING, BlinkState.CLOSED)

        blink.update(0.07)
        assert blink.state == BlinkState.OPENING

        blink.update(0.10)
        assert blink.state == BlinkState.OPEN
        assert blink.coverage == 0.0

    # 8. Blink preserves gaze
    def test_08_blink_preserves_gaze(self):
        ctrl = AvatarController()
        ctrl.look_direction(GazeDirection.RIGHT)
        for _ in range(10):
            ctrl.update(dt=0.05)

        orig_gaze_x = ctrl.state.gaze_x
        assert orig_gaze_x > 0.2

        ctrl.start_blink()
        for _ in range(5):
            st = ctrl.update(dt=0.02)
            assert st.gaze_x > 0.2

    # 9. RMS calculation
    def test_09_pcm_rms_calculation(self):
        silence = b"\x00\x00" * 320
        assert calculate_rms(silence) == 0.0
        assert compute_pcm_rms(silence) == 0.0

        samples = [int(10000.0 * math.sin(i * 0.1)) for i in range(320)]
        pcm = struct.pack("<320h", *samples)
        rms = calculate_rms(pcm)
        assert 6000.0 < rms < 8000.0

    # 10. RMS threshold mapping
    def test_10_rms_threshold_mapping(self):
        assert classify_mouth(200.0) == MouthState.BLANK
        assert classify_mouth(800.0) == MouthState.SLIGHT
        assert classify_mouth(2500.0) == MouthState.MEDIUM
        assert classify_mouth(4500.0) == MouthState.WIDE

    # 11. RMSFilter attack and decay
    def test_11_rms_filter_smoothing(self):
        rf = RMSFilter(attack=0.65, decay=0.25)
        # Step up (attack)
        val1 = rf.update(1000.0)
        assert val1 == 650.0 # 0 + (1000-0)*0.65

        # Step down (decay)
        val2 = rf.update(0.0)
        assert val2 == 650.0 - (650.0 * 0.25) # 487.5

        rf.reset()
        assert rf.value == 0.0

    # 12. IndusEmotionFaceManager orchestration
    def test_12_emotion_face_manager(self):
        mgr = IndusEmotionFaceManager()
        assert mgr.state.emotion == Emotion.NEUTRAL
        assert mgr.state.speaking is False

        mgr.set_emotion(Emotion.HAPPY)
        assert mgr.state.emotion == Emotion.HAPPY

        mgr.set_speaking(True)
        assert mgr.state.speaking is True

        # Process loud audio chunk
        loud_pcm = struct.pack("<160h", *[20000 for _ in range(160)])
        mouth = mgr.lipsync.process_audio(loud_pcm)
        assert mouth in (MouthState.MEDIUM, MouthState.WIDE)

        # Stop speaking resets mouth
        mgr.set_speaking(False)
        assert mgr.state.speaking is False
        assert mgr.state.mouth == MouthState.BLANK

    # 13. Emotion tag compatibility parser
    def test_13_parse_emotion_tag(self):
        assert parse_emotion_tag("[HAPPY] Hello there!") == Emotion.HAPPY
        assert parse_emotion_tag("Let me think [THINKING] about that.") == Emotion.THINKING
        assert parse_emotion_tag("[SAD] I am sorry.") == Emotion.SAD
        assert parse_emotion_tag("Regular conversation without tags") == Emotion.NEUTRAL

    # 14. AssetResolver fallback handling
    def test_14_asset_resolver(self):
        resolver = AssetResolver()
        face_px = resolver.get_face_pixmap(Emotion.NEUTRAL)
        assert face_px is not None or resolver._fallback_pixmap is not None

        mouth_px = resolver.get_mouth_pixmap(MouthState.WIDE)
        assert mouth_px is None or mouth_px.isNull() is False

    # 15. Layered AvatarWidget geometry synchronization
    def test_15_avatar_widget_geometry(self):
        widget = AvatarWidget()
        widget.resize(400, 400)
        widget._sync_geometry()

        assert widget.base.width() == 400
        assert widget.base.height() == 400
        assert widget.mouth.width() == int(400 * 0.42)
        assert widget.mouth.height() == int(400 * 0.22)
        assert widget.mouth.testAttribute(pytest.importorskip("PyQt6.QtCore").Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    # 16. State-dependent gaze controller
    def test_16_state_dependent_gaze(self):
        mgr = IndusEmotionFaceManager()
        gaze_ctrl = GazeController(mgr)
        gaze_ctrl.look_at("left")
        assert mgr.state.gaze == "left"

        gaze_ctrl.return_to_center()
        assert mgr.state.gaze == "center"
        gaze_ctrl.stop()

    # 17. Randomized blink controller
    def test_17_blink_controller(self):
        mgr = IndusEmotionFaceManager()
        blink_ctrl = BlinkController(mgr)
        assert mgr.state.blinking is False

        blink_ctrl.trigger_now()
        assert mgr.state.blinking is True
        blink_ctrl.stop()

    # 18. Thinking and listening states
    def test_18_operational_states(self):
        mgr = IndusEmotionFaceManager()
        mgr.set_state("thinking")
        assert mgr.state.thinking is True
        assert mgr.state.emotion == Emotion.THINKING

        mgr.reset_to_idle()
        assert mgr.state.thinking is False
        assert mgr.state.emotion == Emotion.NEUTRAL
        assert mgr.state.gaze == "center"

    # 19. Empty/malformed audio chunk handling
    def test_19_empty_malformed_audio(self):
        mgr = IndusEmotionFaceManager()
        mgr.process_audio_chunk(b"")
        mgr.process_audio_chunk(b"\x01")
        assert mgr.state.mouth == MouthState.BLANK

    # 20. Easing curves and transitions math
    def test_20_easing_math(self):
        assert ease_in_out_cubic(0.0) == 0.0
        assert ease_in_out_cubic(0.5) == 0.5
        assert ease_in_out_cubic(1.0) == 1.0
        assert clamp(1.5, -1.0, 1.0) == 1.0
        assert clamp(-2.0, -1.0, 1.0) == -1.0
