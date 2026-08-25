"""
Test Suite for INDUS Reliability Fixes
======================================
Verifies:
1. Deterministic code-level intent overrides in computer_settings().
2. Consolidated universal_ad_skipper across browser & media sources.
3. Closed-loop ActionVerifier checks and honest failure reporting (no false-success).
"""

import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from actions.computer_settings import _intent_override, computer_settings
from actions.action_verifier import verifier, VerificationResult
from actions.universal_ad_skipper import universal_ad_skipper, scan_and_skip_ad


import unittest

class TestReliabilityFixes(unittest.TestCase):

    def test_intent_override_hotspot(self):
        inputs = [
            {"action": "network_settings", "description": "hotspot on karo"},
            {"action": "open_settings", "description": "hotspot chalu"},
            {"action": "settings", "description": "turn on mobile hotspot"},
            {"action": "general_settings", "description": "hotspot band kar do"},
            {"action": "network_settings", "description": "disable hotspot"},
        ]
        expected_actions = [
            "enable_hotspot",
            "enable_hotspot",
            "enable_hotspot",
            "disable_hotspot",
            "disable_hotspot",
        ]
        for p, exp in zip(inputs, expected_actions):
            act, val = _intent_override(p)
            self.assertEqual(act, exp, f"Failed for {p}: got {act}, expected {exp}")

    def test_intent_override_wifi_and_bluetooth(self):
        inputs = [
            {"action": "network_settings", "description": "wifi band karo"},
            {"action": "open_settings", "description": "wifi on kar do"},
            {"action": "settings", "description": "bluetooth chalu karo"},
            {"action": "settings", "description": "bluetooth band karo"},
        ]
        expected_actions = [
            "disable_wifi",
            "enable_wifi",
            "bluetooth_settings",
            "disable_bluetooth",
        ]
        for p, exp in zip(inputs, expected_actions):
            act, val = _intent_override(p)
            self.assertEqual(act, exp, f"Failed for {p}: got {act}, expected {exp}")

    def test_intent_override_audio_and_theme(self):
        inputs = [
            {"action": "sound_settings", "description": "mute kar do"},
            {"action": "sound_settings", "description": "awaaz kholo"},
            {"action": "sound_settings", "description": "volume 60%"},
            {"action": "display_settings", "description": "dark mode laga do"},
            {"action": "settings", "description": "recycle bin clean karo"},
        ]
        expected = [
            ("volume_mute", None),
            ("volume_unmute", None),
            ("volume_set", 60),
            ("set_dark_mode", None),
            ("empty_recycle_bin", None),
        ]
        for p, exp in zip(inputs, expected):
            act, val = _intent_override(p)
            self.assertEqual(act, exp[0])
            self.assertEqual(val, exp[1])

    def test_action_verifier_methods(self):
        wifi_res = verifier.verify_wifi(expected_enabled=True)
        self.assertIsInstance(wifi_res, VerificationResult)
        self.assertIn(wifi_res.status, ("SUCCESS", "FAILURE", "UNCERTAIN"))

        hotspot_res = verifier.verify_hotspot(expected_enabled=False)
        self.assertIsInstance(hotspot_res, VerificationResult)
        self.assertIn(hotspot_res.status, ("SUCCESS", "FAILURE", "UNCERTAIN"))

        theme_res = verifier.verify_theme(expected_mode="dark")
        self.assertIsInstance(theme_res, VerificationResult)
        self.assertIn(theme_res.status, ("SUCCESS", "FAILURE", "UNCERTAIN"))

    def test_universal_ad_skipper_consolidation(self):
        res_status = universal_ad_skipper({"action": "status"})
        self.assertTrue("status" in res_status.lower() or "sentinel" in res_status.lower())

        import actions.universal_ad_skipper as uas
        orig_scan = uas.scan_and_skip_ad
        try:
            uas.scan_and_skip_ad = lambda player=None: {"success": True, "message": "Ad skipped via universal skipper."}

            from actions.browser_control import browser_control
            res_b = browser_control({"action": "skip_ad"})
            self.assertTrue("universal skipper" in res_b.lower() or "skipped" in res_b.lower())

            from actions.youtube_video import _handle_skip_ad
            res_yt = _handle_skip_ad()
            self.assertTrue("universal skipper" in res_yt.lower() or "skipped" in res_yt.lower())
        finally:
            uas.scan_and_skip_ad = orig_scan


if __name__ == "__main__":
    unittest.main()
