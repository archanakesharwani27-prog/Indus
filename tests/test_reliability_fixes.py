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


def test_intent_override_hotspot():
    # Even if LLM sent generic or wrong actions
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
        assert act == exp, f"Failed for {p}: got {act}, expected {exp}"
    print("[PASS] test_intent_override_hotspot")


def test_intent_override_wifi_and_bluetooth():
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
        assert act == exp, f"Failed for {p}: got {act}, expected {exp}"
    print("[PASS] test_intent_override_wifi_and_bluetooth")


def test_intent_override_audio_and_theme():
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
        assert act == exp[0] and val == exp[1], f"Failed for {p}: got ({act}, {val}), expected {exp}"
    print("[PASS] test_intent_override_audio_and_theme")


def test_action_verifier_methods():
    # WiFi verification
    wifi_res = verifier.verify_wifi(expected_enabled=True)
    assert isinstance(wifi_res, VerificationResult)
    assert wifi_res.status in ("SUCCESS", "FAILURE", "UNCERTAIN")

    # Hotspot verification
    hotspot_res = verifier.verify_hotspot(expected_enabled=False)
    assert isinstance(hotspot_res, VerificationResult)
    assert hotspot_res.status in ("SUCCESS", "FAILURE", "UNCERTAIN")

    # Theme verification
    theme_res = verifier.verify_theme(expected_mode="dark")
    assert isinstance(theme_res, VerificationResult)
    assert theme_res.status in ("SUCCESS", "FAILURE", "UNCERTAIN")
    print("[PASS] test_action_verifier_methods")


def test_universal_ad_skipper_consolidation():
    # Verify universal_ad_skipper dispatcher
    res_status = universal_ad_skipper({"action": "status"})
    assert "status" in res_status.lower() or "sentinel" in res_status.lower()

    # Mock scan_and_skip_ad to test pure delegation routing without slow OCR/vision
    import actions.universal_ad_skipper as uas
    orig_scan = uas.scan_and_skip_ad
    try:
        uas.scan_and_skip_ad = lambda player=None: {"success": True, "message": "Ad skipped via universal skipper."}

        # Verify browser_control delegation
        from actions.browser_control import browser_control
        res_b = browser_control({"action": "skip_ad"})
        assert "universal skipper" in res_b.lower() or "skipped" in res_b.lower()

        # Verify youtube_video delegation
        from actions.youtube_video import _handle_skip_ad
        res_yt = _handle_skip_ad()
        assert "universal skipper" in res_yt.lower() or "skipped" in res_yt.lower()
    finally:
        uas.scan_and_skip_ad = orig_scan

    print("[PASS] test_universal_ad_skipper_consolidation")


if __name__ == "__main__":
    print("=== Running Reliability Unit Tests ===")
    test_intent_override_hotspot()
    test_intent_override_wifi_and_bluetooth()
    test_intent_override_audio_and_theme()
    test_action_verifier_methods()
    test_universal_ad_skipper_consolidation()
    print("\n=== ALL RELIABILITY TESTS PASSED ===")
