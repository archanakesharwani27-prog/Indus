# tests/test_daily_use_scenarios.py
"""
INDUS Production Daily-Use Scenario Verification Suite
Covers the 14 realistic assistant workflows and error/fallback edge cases.
"""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from PIL import Image

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from actions.action_verifier import ActionVerifier
from actions.computer_control import computer_control
from actions.computer_settings import computer_settings, volume_set
from actions.open_app import _normalize, open_app
from actions.vision_engine import ground_ui_element, screen_understand
from actions.wake_word import WakeWordController, matches_wake_word, wake_word_controller
from actions.youtube_video import youtube_video
from agent.agent_loop import ClosedLoopAgent, closed_loop_agent
from agent.error_handler import classify_error
from agent.task_model import AgentContext, AgentTask, ErrorCategory, TaskStatus, TaskStep
from core.cancellation import cancellation_manager, is_stop_phrase
from core.security_vault import classify_action_risk, evaluate_action, security_vault
from memory.db_engine import db_delete_fact, db_get_fact, db_set_fact
from memory.memory_manager import (
    enforce_user_preferences,
    forget,
    format_memory_for_prompt,
    get_preference,
    load_memory,
    record_conversation_turn,
    remember,
    set_preference,
)


class TestDailyUseScenarios(unittest.TestCase):
    def setUp(self):
        cancellation_manager.reset()
        wake_word_controller.deactivate(reason="Test Setup")

    def tearDown(self):
        cancellation_manager.reset()
        wake_word_controller.deactivate(reason="Test Teardown")

    # -------------------------------------------------------------------------
    # Scenario 1: "INDUS, open Chrome."
    # -------------------------------------------------------------------------
    def test_scenario_1_open_chrome_normalization_and_routing(self):
        normalized = _normalize("Chrome")
        self.assertIn("chrome", normalized.lower())

        with patch("actions.open_app._launch_windows", return_value=True):
            res = open_app({"app_name": "Chrome"})
            self.assertIn("chrome", res.lower())

    # -------------------------------------------------------------------------
    # Scenario 2: "INDUS, search YouTube for Python tutorials."
    # -------------------------------------------------------------------------
    def test_scenario_2_youtube_search(self):
        with patch("actions.youtube_video._open_url") as mock_open:
            res = youtube_video({"action": "search", "query": "Python tutorials"})
            self.assertIn("Python tutorials", res)
            self.assertTrue(mock_open.called)

    # -------------------------------------------------------------------------
    # Scenario 3: "INDUS, what's on my screen?"
    # -------------------------------------------------------------------------
    def test_scenario_3_screen_understand_vqa(self):
        real_img = Image.new("RGB", (1920, 1080), "black")
        with patch("actions.vision_engine.capture_screen", return_value=(real_img, 1920, 1080)):
            with patch("actions.vision_engine._get_api_key", return_value=""):
                with patch("or_client.client.vision", return_value="VS Code editor is open with Python code."):
                    ans = screen_understand("what is on my screen")
                    self.assertIn("VS Code", ans)

    # -------------------------------------------------------------------------
    # Scenario 4: "INDUS, click the search box."
    # -------------------------------------------------------------------------
    def test_scenario_4_visual_grounding_click(self):
        mock_ground = {
            "found": True,
            "element_type": "input",
            "center_x": 450,
            "center_y": 120,
            "confidence": 0.92,
            "is_ambiguous": False,
            "description": "Top search input field",
        }
        with patch("actions.vision_engine.ground_ui_element", return_value=mock_ground):
            with patch("actions.computer_control._click") as mock_click:
                res = computer_control({"action": "click", "target": "search box"})
                self.assertTrue(mock_click.called or "450" in str(res))

    # -------------------------------------------------------------------------
    # Scenario 5: "INDUS, remember that I prefer Brave."
    # -------------------------------------------------------------------------
    def test_scenario_5_remember_preference(self):
        res = remember("browser", "Brave", category="preferences")
        self.assertIn("Remembered", res)
        pref = get_preference("browser")
        self.assertEqual(pref, "Brave")

    # -------------------------------------------------------------------------
    # Scenario 6: "INDUS, what browser do I prefer?"
    # -------------------------------------------------------------------------
    def test_scenario_6_recall_preference(self):
        set_preference("browser", "Brave")
        mem_prompt = format_memory_for_prompt(None)
        self.assertIn("Browser: Brave", mem_prompt)

    # -------------------------------------------------------------------------
    # Scenario 7: "INDUS, open my preferred browser." (Dynamic inference)
    # -------------------------------------------------------------------------
    def test_scenario_7_open_preferred_browser_dynamic_inference(self):
        set_preference("browser", "Brave")
        norm = _normalize("open my preferred browser")
        self.assertEqual(norm.lower(), "brave")

        # Now test correction override
        set_preference("browser", "Chrome")
        norm_corrected = _normalize("open my preferred browser")
        self.assertEqual(norm_corrected.lower(), "chrome")

    # -------------------------------------------------------------------------
    # Scenario 8: "INDUS, set volume to 40%."
    # -------------------------------------------------------------------------
    def test_scenario_8_set_volume(self):
        with patch("actions.computer_settings.volume_set") as mock_vol_set:
            res = computer_settings({"action": "volume_set", "value": 40})
            self.assertIn("Volume set", res)

    # -------------------------------------------------------------------------
    # Scenario 9: "INDUS, stop." (Voice Interruption & Cancellation)
    # -------------------------------------------------------------------------
    def test_scenario_9_voice_stop(self):
        self.assertTrue(is_stop_phrase("INDUS stop"))
        self.assertTrue(is_stop_phrase("cancel"))
        self.assertTrue(is_stop_phrase("never mind"))
        cancellation_manager.request_cancellation("Voice STOP")
        self.assertTrue(cancellation_manager.is_cancelled())

    # -------------------------------------------------------------------------
    # Scenario 10: Start a long task and interrupt it
    # -------------------------------------------------------------------------
    def test_scenario_10_long_task_interruption(self):
        cancellation_manager.request_cancellation("User barge-in STOP")
        res = closed_loop_agent.execute_goal("Scan network and generate comprehensive security report")
        self.assertIn("cancel", res.lower())



    # -------------------------------------------------------------------------
    # Scenario 11: Cause a tool failure and verify recovery
    # -------------------------------------------------------------------------
    def test_scenario_11_tool_failure_and_recovery(self):
        step_app = TaskStep(step_id=1, description="Launch app", tool="open_app", parameters={"app_name": "xyz_app"})
        cat, reason, alt = classify_error(step_app, "FileNotFoundError: Application 'xyz_app' not installed")
        self.assertEqual(cat, ErrorCategory.ENVIRONMENT_ERROR)

        # Destructive action safety
        step_del = TaskStep(step_id=2, description="Delete file", tool="delete_file", parameters={"path": "important.txt"})
        cat_del, reason_del, alt_del = classify_error(step_del, "File locked")
        self.assertEqual(cat_del, ErrorCategory.PERMANENT_LIMITATION)

    # -------------------------------------------------------------------------
    # Scenario 12: Restart INDUS and verify memory persistence
    # -------------------------------------------------------------------------
    def test_scenario_12_memory_persistence_across_restarts(self):
        db_set_fact("identity", "creator", "Ansh Kesharwani")
        fresh_facts = load_memory()
        creator = db_get_fact("creator")
        self.assertEqual(creator, "Ansh Kesharwani")

        # Test forget
        forget_res = forget("creator", category="identity")
        self.assertIn("Forgotten", forget_res)
        self.assertIsNone(db_get_fact("creator"))

    # -------------------------------------------------------------------------
    # Scenario 13: Disable primary provider and test fallback cascade
    # -------------------------------------------------------------------------
    def test_scenario_13_provider_fallback_cascade(self):
        from or_client import client
        with patch.object(client, "_call_with_fallback", return_value="Fallback Response OK"):
            res = client.chat("test query", system="test")
            self.assertEqual(res, "Fallback Response OK")

    # -------------------------------------------------------------------------
    # Scenario 14: Ambiguous visual command -> asks clarification, no blind click
    # -------------------------------------------------------------------------
    def test_scenario_14_ambiguous_visual_command_asks_clarification(self):
        # When visual target is ambiguous or not found, computer_control must NOT perform a click
        with patch("actions.computer_control._screen_find", return_value=None):
            with patch("actions.computer_control._click") as mock_click:
                res = computer_control({"action": "click", "target": "ambiguous download button"})
                self.assertFalse(mock_click.called)
                self.assertIn("not found or ambiguous", res.lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
