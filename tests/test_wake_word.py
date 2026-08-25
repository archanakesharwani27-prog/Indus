import sys
import time
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from actions.wake_word import (
    WakeWordController,
    matches_wake_word,
    is_standby_phrase,
    WAKE_WORDS,
)
from core.cancellation import cancellation_manager


class TestWakeWordAndActivation(unittest.TestCase):

    def setUp(self):
        cancellation_manager.reset()
        self.controller = WakeWordController(inactivity_timeout=0.5)

    def tearDown(self):
        cancellation_manager.reset()

    # 1. Wake Word Match Detection Test
    def test_matches_wake_word(self):
        self.assertIsNotNone(matches_wake_word("indus"))
        self.assertIsNotNone(matches_wake_word("hey indus"))
        self.assertIsNotNone(matches_wake_word("hello indus open youtube"))
        self.assertIsNotNone(matches_wake_word("hey jarvis"))
        self.assertIsNotNone(matches_wake_word("jarvis what time is it"))

    # 2. Wake Word Negative Test
    def test_wake_word_negative(self):
        self.assertIsNone(matches_wake_word("what is the weather today"))
        self.assertIsNone(matches_wake_word("play music"))
        self.assertIsNone(matches_wake_word(""))

    # 3. False Positive Protection
    def test_false_positive_protection(self):
        # 'industry' or 'individual' should not trigger exact word boundary 'indus'
        self.assertIsNone(matches_wake_word("the tech industry is growing fast"))
        self.assertIsNone(matches_wake_word("an individual contributor"))

    # 4. Activation State & Audio Forwarding Test
    def test_activation_and_audio_gating(self):
        self.assertFalse(self.controller.is_active)

        # In standby: feed_audio must return False (DO NOT forward to Gemini)
        dummy_pcm = b"\x00\x00" * 512
        forward_in_standby = self.controller.feed_audio(dummy_pcm, rms=10.0)
        self.assertFalse(forward_in_standby, "Standby audio must not be forwarded to cloud")

        # Activate
        self.controller.activate(source="Wake Word 'INDUS'")
        self.assertTrue(self.controller.is_active)

        # While active: feed_audio must return True (forward to Gemini)
        forward_when_active = self.controller.feed_audio(dummy_pcm, rms=50.0)
        self.assertTrue(forward_when_active, "Active audio must be forwarded to cloud")

    # 5. Standby Voice Command Recognition
    def test_standby_commands(self):
        self.assertTrue(is_standby_phrase("go to sleep"))
        self.assertTrue(is_standby_phrase("standby"))
        self.assertTrue(is_standby_phrase("shant ho jao"))
        self.assertTrue(is_standby_phrase("so jao"))
        self.assertFalse(is_standby_phrase("open chrome browser"))

    # 6. Inactivity Timeout Auto-Standby Test
    def test_inactivity_timeout(self):
        self.controller.activate(source="Test")
        self.assertTrue(self.controller.is_active)

        # Wait for timeout (0.5s configured in setUp)
        time.sleep(0.6)
        self.controller.check_inactivity()
        self.assertFalse(self.controller.is_active, "Controller should return to standby after timeout")

    # 7. Activity Reset (Touch) Prevents Premature Standby
    def test_touch_resets_inactivity_timer(self):
        self.controller.activate(source="Test")
        self.assertTrue(self.controller.is_active)

        # Simulate ongoing user speech after 0.3s
        time.sleep(0.3)
        self.controller.touch()

        # Check after 0.3s (total 0.6s since activation, but only 0.3s since touch)
        time.sleep(0.3)
        self.controller.check_inactivity()
        self.assertTrue(self.controller.is_active, "Touch should have extended active session")

    # 8. Cancellation Compatibility Test
    def test_cancellation_compatibility(self):
        self.controller.activate(source="Wake Word")
        self.assertTrue(self.controller.is_active)

        # Trigger voice stop
        cancellation_manager.request_cancellation(reason="Voice STOP")
        self.assertTrue(cancellation_manager.is_cancelled())

        # Reset cancellation
        cancellation_manager.reset()
        self.assertFalse(cancellation_manager.is_cancelled())

    # 9. Real E2E Activation and Deactivation Callback Test
    def test_real_e2e_activation_callbacks(self):
        events = []

        def on_act(src, buf):
            events.append(f"ACTIVATED:{src}")

        def on_deact(reason):
            events.append(f"DEACTIVATED:{reason}")

        custom_controller = WakeWordController(
            inactivity_timeout=0.2,
            on_activate=on_act,
            on_deactivate=on_deact
        )

        custom_controller.activate(source="indus")
        self.assertIn("ACTIVATED:indus", events)

        time.sleep(0.3)
        custom_controller.check_inactivity()
        self.assertTrue(any("DEACTIVATED" in e for e in events))


if __name__ == "__main__":
    unittest.main()
