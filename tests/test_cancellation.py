import sys
import time
import threading
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.cancellation import cancellation_manager, is_stop_phrase, STOP_PATTERNS
from actions.deep_research import deep_research
from actions.open_app import open_app
from actions.computer_settings import computer_settings


class TestVoiceInterruptionAndCancellation(unittest.TestCase):

    def setUp(self):
        cancellation_manager.reset()

    def tearDown(self):
        cancellation_manager.reset()

    # 1. Deterministic Interruption Phrase Matching Test
    def test_is_stop_phrase(self):
        # Explicit stop phrases
        self.assertTrue(is_stop_phrase("stop"))
        self.assertTrue(is_stop_phrase("INDUS stop"))
        self.assertTrue(is_stop_phrase("cancel that"))
        self.assertTrue(is_stop_phrase("please abort"))
        self.assertTrue(is_stop_phrase("never mind"))
        self.assertTrue(is_stop_phrase("shut up"))
        self.assertTrue(is_stop_phrase("ruko"))
        self.assertTrue(is_stop_phrase("bas"))
        self.assertTrue(is_stop_phrase("band karo"))

        # Conversational false-positive avoidance
        self.assertFalse(is_stop_phrase("kal bus stop par milenge sab dost log"))
        self.assertFalse(is_stop_phrase("what is the best non-stop flight to delhi"))
        self.assertFalse(is_stop_phrase(""))
        self.assertFalse(is_stop_phrase("play music on youtube"))

    # 2. Stop While Task Is Executing
    def test_cancellation_while_task_executing(self):
        cancellation_manager.set_active_task("dummy_long_task")
        self.assertEqual(cancellation_manager.active_task, "dummy_long_task")
        self.assertFalse(cancellation_manager.is_cancelled())

        # Trigger cancellation mid-task
        cancellation_manager.request_cancellation(reason="Voice stop")
        self.assertTrue(cancellation_manager.is_cancelled())

    # 3. Stop While TTS Is Playing / Callback Propagation
    def test_tts_interruption_callback(self):
        callback_called = []

        def mock_tts_flusher(reason):
            callback_called.append(reason)

        cancellation_manager.register_callback(mock_tts_flusher)
        cancellation_manager.request_cancellation(reason="User said stop")

        self.assertEqual(len(callback_called), 1)
        self.assertEqual(callback_called[0], "User said stop")
        cancellation_manager.unregister_callback(mock_tts_flusher)

    # 4. Stop Prevents Queued Actions
    def test_stop_prevents_queued_actions(self):
        cancellation_manager.request_cancellation(reason="Interruption")

        # Long running research should exit immediately
        res = deep_research("IPL standings 2025", "sports")
        self.assertIn("cancelled", res.lower())

    # 5. Non-cancellable / Atomic Actions Handled Safely
    def test_atomic_action_safe_handling(self):
        # Setting volume is an atomic hardware action
        cancellation_manager.reset()
        res = computer_settings({"action": "set_volume", "value": "28"})
        self.assertIn("Volume set to 28%", res)

    # 6. Cancellation Is Idempotent & Repeated Stops Do Not Crash
    def test_cancellation_idempotent(self):
        cancellation_manager.request_cancellation("Stop 1")
        cancellation_manager.request_cancellation("Stop 2")
        cancellation_manager.request_cancellation("Stop 3")
        self.assertTrue(cancellation_manager.is_cancelled())

    # 7. Normal Commands Still Work After Reset
    def test_normal_commands_work_after_reset(self):
        cancellation_manager.request_cancellation("User cancel")
        self.assertTrue(cancellation_manager.is_cancelled())

        # Reset for new conversational turn
        cancellation_manager.reset()
        self.assertFalse(cancellation_manager.is_cancelled())
        self.assertIsNone(cancellation_manager.active_task)

    # 8. Real Safe E2E Cancellation Test
    def test_real_safe_e2e_cancellation(self):
        # Start a thread simulating a background long task
        task_finished = threading.Event()
        task_result = []

        def long_running_worker():
            cancellation_manager.set_active_task("simulated_research")
            for _ in range(20):
                if cancellation_manager.is_cancelled():
                    task_result.append("CANCELLED")
                    task_finished.set()
                    return
                time.sleep(0.05)
            task_result.append("COMPLETED")
            task_finished.set()

        t = threading.Thread(target=long_running_worker)
        t.start()

        # Simulate user voice interruption after 50ms
        time.sleep(0.05)
        cancellation_manager.request_cancellation("User voice 'Stop'")
        task_finished.wait(timeout=2.0)

        self.assertEqual(task_result, ["CANCELLED"])


if __name__ == "__main__":
    unittest.main()
