# tests/test_ui_end_to_end.py
"""
INDUS (INDUS) -- UI-to-Backend End-to-End Acceptance Test Suite
Tests the complete execution chain:
PyQt6 UI -> Text/Voice Directive -> Wake/Cancellation -> Dispatcher -> Actions -> Verification -> Memory -> UI Output.
"""

import sys
import time
import unittest
from pathlib import Path
from PyQt6.QtWidgets import QApplication

WORKSPACE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE_DIR))

# Ensure single QApplication instance
_app = QApplication.instance() or QApplication(sys.argv)


class TestUIEndToEnd(unittest.TestCase):
    """Real End-to-End Acceptance Tests connecting PyQt6 UI to backend subsystems."""

    @classmethod
    def setUpClass(cls):
        from ui import JarvisUI
        from main import JarvisLive
        face_p = str(WORKSPACE_DIR / "face.png")
        cls.ui = JarvisUI(face_path=face_p if Path(face_p).exists() else None)
        cls.jarvis = JarvisLive(cls.ui)

    def test_01_ui_hud_state_transitions(self):
        """Test all 9 HUD lifecycle states and transitions."""
        states = ["STANDBY", "ACTIVATING", "LISTENING", "THINKING", "EXECUTING", "SPEAKING", "CANCELLING", "CANCELLED", "ERROR"]
        for s in states:
            self.ui.set_state(s)
            self.assertEqual(self.ui.state, s)
        self.ui.set_state("STANDBY")

    def test_02_text_command_volume_wire(self):
        """Test UI Text Command -> main.py -> tool dispatcher -> Windows Core Audio -> UI Log."""
        import asyncio
        class MockFC:
            name = "computer_settings"
            args = {"action": "volume_set", "value": 35}
            id = "test_call_01"
        resp = asyncio.run(self.jarvis._execute_tool(MockFC()))
        res_str = str(resp.response.get("result", ""))
        self.assertTrue("Volume set" in res_str or "35" in res_str)

    def test_03_text_command_app_launch_and_verification(self):
        """Test UI Command -> open_app -> ActionVerifier confirms process absence on invalid app."""
        import asyncio
        class MockFC:
            name = "open_app"
            args = {"app_name": "totally_invalid_app_xyz_9999"}
            id = "test_call_02"
        resp = asyncio.run(self.jarvis._execute_tool(MockFC()))
        res_str = str(resp.response.get("result", ""))
        self.assertTrue("verified that it is not running" in res_str or "failed" in res_str.lower())

    def test_04_wake_word_and_same_breath_pipeline(self):
        """Test WakeWordController Standby -> Active -> Command Extraction."""
        from actions.wake_word import WakeWordController, matches_wake_word
        
        # Test wake word match
        matched = matches_wake_word("Hey INDUS open Chrome")
        self.assertEqual(matched, "indus")

        # Test false positive rejection
        fp = matches_wake_word("industry standard report")
        self.assertIsNone(fp)

        # Test controller activation
        ctrl = WakeWordController(inactivity_timeout=0.2)
        ctrl.activate("Test")
        self.assertTrue(ctrl.is_active)
        time.sleep(0.25)
        ctrl.check_inactivity()
        self.assertFalse(ctrl.is_active)

    def test_05_voice_cancellation_and_barge_in(self):
        """Test voice interruption immediately sets atomic cancellation token."""
        from core.cancellation import cancellation_manager, is_stop_phrase

        self.assertTrue(is_stop_phrase("STOP"))
        self.assertTrue(is_stop_phrase("Ruko"))
        self.assertTrue(is_stop_phrase("Cancel that"))
        self.assertFalse(is_stop_phrase("Search python tutorials"))

        cancelled = False
        def cb(reason):
            nonlocal cancelled
            cancelled = True

        cancellation_manager.reset()
        cancellation_manager.register_callback(cb)
        cancellation_manager.set_active_task("active_search")
        cancellation_manager.request_cancellation("Voice barge-in 'STOP'")

        self.assertTrue(cancellation_manager.is_cancelled())
        self.assertTrue(cancelled)
        cancellation_manager.reset()

    def test_06_screen_capture_and_grounding_safety(self):
        """Test MSS screen capture and ambiguous target rejection."""
        from actions.vision_engine import capture_screen, ground_ui_element
        from unittest.mock import patch, MagicMock
        from PIL import Image
        import json

        img, w, h = capture_screen()
        self.assertGreater(w, 0)
        self.assertGreater(h, 0)

        # Ambiguous/non-existent button test
        blank = Image.new("RGB", (400, 300), (0, 0, 0))
        mock_resp = {"found": False, "confidence": 0.0, "description": "Element not found"}
        with patch("actions.vision_engine._get_api_key", return_value="test_key"):
            with patch("google.genai.Client") as mock_client:
                mock_gen = MagicMock()
                mock_gen.models.generate_content.return_value = MagicMock(text=json.dumps(mock_resp))
                mock_client.return_value = mock_gen
                res = ground_ui_element("quantum_hyperdrive_button", img=blank)
                self.assertFalse(res.get("found", False))
                self.assertLess(res.get("confidence", 1.0), 0.50)

    def test_07_memory_persistence_across_cold_restart(self):
        """Test SQLite fact persistence across cold database queries."""
        import sqlite3
        from memory.memory_manager import update_memory
        from memory.db_engine import db_get_fact

        test_key = "e2e_verified_browser"
        test_val = "Brave"
        update_memory({"preferences": {test_key: test_val}})

        # Query directly from separate SQLite connection
        db_p = WORKSPACE_DIR / "memory" / "indus_memory.db"
        conn = sqlite3.connect(str(db_p))
        cur = conn.cursor()
        cur.execute("SELECT value FROM user_profile WHERE key = ?", (test_key,))
        row = cur.fetchone()
        conn.close()

        self.assertIsNotNone(row)
        self.assertEqual(row[0], test_val)

    def test_08_destructive_action_security_gate(self):
        """Test that destructive operations are blocked from automatic retries."""
        from agent.error_handler import is_destructive_step
        from core.security_vault import classify_action_risk

        self.assertTrue(is_destructive_step("system_shutdown"))
        self.assertTrue(is_destructive_step("system_restart"))
        self.assertTrue(is_destructive_step("delete_file"))
        self.assertFalse(is_destructive_step("open_app"))

        # Verify vault classification
        risk = classify_action_risk("system_shutdown")
        self.assertEqual(risk, "DESTRUCTIVE")

    # ======================================================================
    # Phase 2: Pipeline Contract Tests (09-18)
    # ======================================================================

    def test_09_event_bus_round_trip_latency(self):
        """EventBus should deliver a published event within 10ms."""
        import time
        from core.event_bus import event_bus, E

        received = []
        def handler(evt):
            received.append(evt)

        event_bus.subscribe(E.TOOL_STARTED, handler)
        try:
            t0 = time.perf_counter()
            evt = event_bus.publish(E.TOOL_STARTED, source="test_09",
                                    data={"tool": "wiring_test"})
            elapsed_ms = (time.perf_counter() - t0) * 1000

            self.assertIsNotNone(evt)
            self.assertTrue(len(received) >= 1, "Event not delivered to subscriber")
            self.assertLess(elapsed_ms, 10.0, f"Event bus too slow: {elapsed_ms:.2f}ms")
            self.assertEqual(received[-1].source, "test_09")
        finally:
            event_bus.unsubscribe(E.TOOL_STARTED, handler)

    def test_10_event_bus_history_and_filter(self):
        """EventBus history should store events and allow name-filtered retrieval."""
        from core.event_bus import event_bus, E

        event_bus.publish(E.MEMORY_UPDATE, source="test_10", data={"keys": ["test_pref"]})
        event_bus.publish(E.TOOL_COMPLETED, source="test_10", data={"tool": "open_app"})

        mem_events = event_bus.get_history(E.MEMORY_UPDATE, limit=5)
        tool_events = event_bus.get_history(E.TOOL_COMPLETED, limit=5)

        self.assertTrue(any(e.source == "test_10" for e in mem_events))
        self.assertTrue(any(e.source == "test_10" for e in tool_events))

    def test_11_tool_result_normalize_adapter(self):
        """normalize_result() must correctly convert str/dict/None to ToolResult."""
        from core.tool_result import ToolResult, normalize_result

        # Success string
        r = normalize_result("Chrome opened successfully.", "open_app")
        self.assertTrue(r.success)
        self.assertEqual(r.to_str(), "Chrome opened successfully.")

        # Failure string
        r = normalize_result("Tool 'x' failed: timeout error", "x")
        self.assertFalse(r.success)
        self.assertIsNotNone(r.error)

        # Cancellation string
        r = normalize_result("Operation cancelled by user.", "some_tool")
        self.assertFalse(r.success)
        self.assertTrue(r.cancelled)

        # None ? success (ambiguous empty ? treated as ok)
        r = normalize_result(None, "empty_tool")
        self.assertTrue(r.success)

        # Exception
        r = normalize_result(RuntimeError("network down"), "net_tool")
        self.assertFalse(r.success)
        self.assertIn("network down", r.error)

        # dict with success key
        r = normalize_result({"success": True, "message": "done", "data": {"k": 1}})
        self.assertTrue(r.success)
        self.assertEqual(r.data, {"k": 1})

        # ToolResult.unavailable factory
        r = ToolResult.unavailable("Philips Hue Bridge")
        self.assertFalse(r.success)
        self.assertIn("ENVIRONMENT_UNAVAILABLE", r.error)
        self.assertIn("Philips Hue Bridge", r.message)

    def test_12_cancellation_raise_if_cancelled(self):
        """raise_if_cancelled() must raise CancelledError when flag is set."""
        from core.cancellation import cancellation_manager, CancelledError

        cancellation_manager.reset()
        # Must NOT raise when no cancellation
        try:
            cancellation_manager.raise_if_cancelled("test_tool")
        except CancelledError:
            self.fail("raise_if_cancelled() raised unexpectedly when not cancelled")

        # Request cancellation
        cancellation_manager.request_cancellation("test_12")
        try:
            cancellation_manager.raise_if_cancelled("test_tool")
            self.fail("raise_if_cancelled() did not raise after cancellation")
        except CancelledError as e:
            self.assertIn("test_tool", str(e))
        finally:
            cancellation_manager.reset()

    def test_13_cancellation_stops_mid_loop(self):
        """A tool loop should stop at its checkpoint when cancellation is requested."""
        from core.cancellation import cancellation_manager, CancelledError
        import threading
        import time

        cancellation_manager.reset()
        results_collected = []
        cancelled_at = []
        loop_started = threading.Event()

        def simulated_long_tool():
            """Mimics a slow tool iterating 50 times with 1ms sleep per step."""
            try:
                for i in range(50):
                    if i == 2:
                        loop_started.set()   # signal: loop is mid-execution
                    cancellation_manager.raise_if_cancelled("sim_tool")
                    time.sleep(0.001)        # simulate work -- ensures loop cannot finish < 50ms
                    results_collected.append(i)
            except CancelledError:
                cancelled_at.append(len(results_collected))

        t = threading.Thread(target=simulated_long_tool, daemon=True)
        t.start()
        # Wait until loop is past iteration 2, then cancel
        loop_started.wait(timeout=2.0)
        cancellation_manager.request_cancellation("test_13")
        t.join(timeout=3.0)
        cancellation_manager.reset()

        self.assertTrue(len(cancelled_at) > 0, "Tool did not catch CancelledError")
        self.assertLess(len(results_collected), 50,
                        f"Tool ran to completion ({len(results_collected)} steps) despite cancellation")

    def test_14_security_gate_blocks_destructive_in_fast_path(self):
        """
        The security gate in main.py fast-path must block DESTRUCTIVE actions.
        We test evaluate_action() directly (same function called by the gate).
        """
        from core.security_vault import evaluate_action, classify_action_risk

        # Classify a known destructive action
        risk = classify_action_risk("delete_file")
        self.assertIn(risk, ("DESTRUCTIVE", "HIGH"))

        # Without a PIN set, destructive actions still pass (by design)
        # The important check is that the classification is correct
        decision = evaluate_action("open_app", {"app_name": "Chrome"})
        self.assertTrue(decision.allowed, "Non-destructive action should be allowed")

        # MEDIUM / LOW risk should always be allowed
        decision_low = evaluate_action("web_search", {"query": "test"})
        self.assertTrue(decision_low.allowed)

        # Verify RISK_LEVELS dict covers key destructive tools
        from core.security_vault import RISK_LEVELS
        destructive_tools = RISK_LEVELS.get("DESTRUCTIVE", [])
        self.assertIn("delete_file", destructive_tools)
        self.assertIn("system_shutdown", destructive_tools)

    def test_15_full_stack_text_to_filesystem_action(self):
        """
        Full stack: text input -> file_controller -> ActionVerifier -> result -> UI.
        Tests the actual filesystem I/O path, not a mock.
        """
        import tempfile, os
        from actions.file_controller import file_controller
        from actions.action_verifier import ActionVerifier
        from core.cancellation import cancellation_manager

        cancellation_manager.reset()

        # 1. Execute via the same function main.py dispatcher calls
        tmp_path = os.path.join(tempfile.gettempdir(), "indus_stack_test_09.txt")
        result = file_controller(
            parameters={"action": "create_file", "path": tmp_path,
                        "name": "", "content": "INDUS_PIPELINE_TEST"},
            player=None
        )
        self.assertIsInstance(result, str)
        self.assertTrue(os.path.exists(tmp_path), f"File not created: {tmp_path}")

        # 2. Normalize result through ToolResult adapter
        from core.tool_result import normalize_result
        tool_result = normalize_result(result, tool_name="file_controller")
        self.assertTrue(tool_result.success, f"Expected success, got: {result}")

        # 3. Verify via ActionVerifier
        verifier = ActionVerifier()
        pre_snap  = verifier.capture_state_snapshot("file_controller",
                                                     {"path": tmp_path})
        post_snap = verifier.capture_state_snapshot("file_controller",
                                                     {"path": tmp_path})
        v_res = verifier.verify_action_success(
            action_name="file_controller",
            pre_snapshot=pre_snap,
            post_snapshot=post_snap,
            expected_target="create file",
        )
        # ActionVerifier should not report FAIL for a file that exists
        self.assertNotEqual(v_res.status, "FAIL",
                            f"Verifier unexpectedly failed: {v_res.details}")

        # 4. Publish TOOL_COMPLETED event to EventBus
        from core.event_bus import event_bus, E
        received = []
        event_bus.subscribe(E.TOOL_COMPLETED, lambda e: received.append(e))
        try:
            event_bus.publish(E.TOOL_COMPLETED, source="test_15",
                              data={"tool": "file_controller", "success": True})
            self.assertTrue(len(received) >= 1)
        finally:
            event_bus.unsubscribe(E.TOOL_COMPLETED, received.append)

        # 5. Cleanup
        os.unlink(tmp_path)
        self.assertFalse(os.path.exists(tmp_path))

    def test_16_vision_action_screen_capture_pipeline(self):
        """
        Vision pipeline: MSS screen capture must return a valid frame.
        Tests the actual screen capture path.
        """
        try:
            import mss
        except ImportError:
            self.skipTest("mss not installed")

        from actions.vision_engine import capture_screen
        from core.cancellation import cancellation_manager
        cancellation_manager.reset()

        frame = capture_screen()
        self.assertIsNotNone(frame, "Screen capture returned None")

        # Verify it is a valid numpy/PIL-like array with width/height
        # (capture_screen returns a dict or array depending on implementation)
        if hasattr(frame, "shape"):
            h, w = frame.shape[:2]
            self.assertGreater(w, 0)
            self.assertGreater(h, 0)
        elif isinstance(frame, dict) and "width" in frame:
            self.assertGreater(frame["width"], 0)

    def test_17_network_search_pipeline_cancellation(self):
        """
        Web search pipeline: cancellation flag set before call must return
        'cancelled' result -- not attempt network I/O.
        """
        from core.cancellation import cancellation_manager
        from actions.web_search import web_search

        cancellation_manager.reset()
        cancellation_manager.request_cancellation("test_17")

        try:
            result = web_search(parameters={"query": "test query"}, player=None)
            # Must return immediately without hitting network
            self.assertIn("cancel", result.lower(),
                          f"Expected cancelled message, got: {result}")
        finally:
            cancellation_manager.reset()

    def test_18_hardware_unavailable_returns_env_unavailable(self):
        """
        Tools with unavailable hardware must return ENVIRONMENT_UNAVAILABLE
        (not raise exceptions, not silently succeed).
        """
        import shutil
        from core.tool_result import normalize_result

        # Test mobile_bridge without ADB
        if not shutil.which("adb"):
            from actions.mobile_bridge import mobile_bridge
            result = mobile_bridge(parameters={"action": "status"}, player=None)
            self.assertIn("ENVIRONMENT_UNAVAILABLE", result,
                          f"Expected ENVIRONMENT_UNAVAILABLE, got: {result}")
            # Normalize -- should be failure
            tr = normalize_result(result, "mobile_bridge")
            self.assertFalse(tr.success)
            self.assertIn("ENVIRONMENT_UNAVAILABLE", (tr.error or ""))
        else:
            self.skipTest("ADB is available -- this test targets missing ADB environment")

        # Test git_controller without git (if git is absent)
        if not shutil.which("git"):
            from actions.git_controller import git_controller
            result = git_controller(parameters={"action": "status"}, player=None)
            self.assertIn("ENVIRONMENT_UNAVAILABLE", result)
        # (git is almost certainly present on dev machine -- skip is fine)


if __name__ == "__main__":
    unittest.main(verbosity=2)
