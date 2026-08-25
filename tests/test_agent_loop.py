import sys
import time
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from agent.task_model import AgentTask, TaskStep, TaskStatus, ErrorCategory, agent_context
from agent.planner import validate_plan_schema, create_agent_plan, replan_remaining_steps
from agent.error_handler import classify_error, generate_alternative_step, is_destructive_step
from agent.agent_loop import ClosedLoopAgent, is_direct_chat_query
from core.cancellation import cancellation_manager
from memory.memory_manager import set_preference, get_preference


class TestAgentExecutionLoop(unittest.TestCase):

    def setUp(self):
        cancellation_manager.reset()
        self.agent = ClosedLoopAgent()

    def tearDown(self):
        cancellation_manager.reset()

    # 1. Direct Chat vs Action Classification Test
    def test_direct_chat_detection(self):
        self.assertTrue(is_direct_chat_query("hello"))
        self.assertTrue(is_direct_chat_query("who made you"))
        self.assertTrue(is_direct_chat_query("tell me a joke"))
        self.assertFalse(is_direct_chat_query("open chrome and go to youtube"))
        self.assertFalse(is_direct_chat_query("set volume to 50%"))

    # 2. Direct Chat Execution Bypasses Planning
    def test_direct_chat_execution(self):
        res = self.agent.execute_goal("who are you")
        self.assertIsInstance(res, str)
        self.assertTrue(len(res) > 0)
        # Should NOT create a multi-step task
        self.assertIsNone(self.agent.current_task)

    # 3. Plan Validation and Malformed Plan Rejection
    def test_plan_validation_and_malformed_rejection(self):
        # Valid plan
        valid_raw = {
            "goal": "Open Notepad and type hello",
            "steps": [
                {"step_id": 1, "tool": "open_app", "description": "Open Notepad", "parameters": {"app_name": "notepad"}},
                {"step_id": 2, "tool": "computer_control", "description": "Type hello", "parameters": {"action": "type", "text": "hello"}},
            ]
        }
        steps = validate_plan_schema(valid_raw)
        self.assertEqual(len(steps), 2)
        self.assertEqual(steps[0].tool, "open_app")

        # Malformed plan (missing steps)
        with self.assertRaises(ValueError):
            validate_plan_schema({"goal": "invalid"})

        # Unknown tool fallback
        unknown_tool_raw = {
            "goal": "Find a button",
            "steps": [{"step_id": 1, "tool": "magical_clicker_tool", "description": "click download"}]
        }
        steps2 = validate_plan_schema(unknown_tool_raw)
        self.assertEqual(steps2[0].tool, "vision_click")

    # 4. Single-Step Task Execution & Verification
    def test_single_step_execution(self):
        # Safe reversible action: volume set
        res = self.agent.execute_goal("Set volume to 25%")
        self.assertIn("completed", res.lower())
        self.assertIsNotNone(self.agent.current_task)
        self.assertEqual(self.agent.current_task.status, TaskStatus.COMPLETED)

    # 5. Multi-Step Task Execution & Verification
    def test_multi_step_execution(self):
        # Multi-step safe task
        res = self.agent.execute_goal("Set volume to 30% and check volume status")
        self.assertIn("completed", res.lower())
        self.assertEqual(self.agent.current_task.status, TaskStatus.COMPLETED)
        self.assertGreaterEqual(len(self.agent.current_task.completed_steps), 1)

    # 6. Error Classification: Transient vs Environment vs Security
    def test_error_classification(self):
        step = TaskStep(step_id=1, tool="open_app", description="Open App", max_retries=2)

        # Transient
        cat, reason, alt = classify_error(step, "Network connection timed out", attempt=1)
        self.assertEqual(cat, ErrorCategory.TRANSIENT)

        # Environment / Element not found
        cat2, reason2, alt2 = classify_error(step, "Element not found on screen", attempt=1)
        self.assertEqual(cat2, ErrorCategory.ENVIRONMENT_ERROR)

        # Security denial
        cat3, reason3, alt3 = classify_error(step, "Action blocked by security vault policy", attempt=1)
        self.assertEqual(cat3, ErrorCategory.SECURITY_DENIAL)

    # 7. Alternative Strategy Generation
    def test_alternative_strategy_generation(self):
        step = TaskStep(step_id=1, tool="computer_control", description="Click Download", parameters={"action": "click", "target": "Download"}, executed_strategy="primary")
        alt = generate_alternative_step(step, ErrorCategory.ENVIRONMENT_ERROR, "Try vision grounding")
        self.assertIsNotNone(alt)
        self.assertEqual(alt.tool, "vision_click")
        self.assertEqual(alt.executed_strategy, "vision_grounding")

    # 8. Destructive Actions Never Auto-Retried
    def test_destructive_actions_never_retried(self):
        step = TaskStep(step_id=1, tool="file_controller", description="delete system folder", parameters={"action": "delete"})
        self.assertTrue(is_destructive_step(step))

        cat, reason, alt = classify_error(step, "File lock error", attempt=1)
        self.assertEqual(cat, ErrorCategory.PERMANENT_LIMITATION)

        alt_step = generate_alternative_step(step, cat, alt)
        self.assertIsNone(alt_step, "Destructive steps must never produce automated retry steps")

    # 9. Cancellation During Multi-Step Execution
    def test_cancellation_during_multi_step_task(self):
        cancellation_manager.request_cancellation(reason="Voice STOP")
        res = self.agent.execute_goal("Open Chrome and navigate to Google and set volume to 50%")
        self.assertIn("cancelled", res.lower())

    # 10. Task Timeout Guardrail
    def test_task_timeout(self):
        task = AgentTask.create(goal="Long Task", timeout_seconds=0.1)
        time.sleep(0.15)
        self.assertTrue(task.is_timed_out())

    # 11. Conversational Continuation & Anaphora Resolution
    def test_conversational_continuation(self):
        agent_context.update_context(app="Chrome", target="Downloads folder")
        resolved = agent_context.resolve_anaphora("Open it now")
        self.assertIn("Downloads folder", resolved)

        resolved_hi = agent_context.resolve_anaphora("Usko band karo")
        self.assertIn("Downloads folder", resolved_hi)

    # 12. Memory Retrieval Influence Test
    def test_memory_retrieval_integration(self):
        # Set a test preference in memory
        set_preference("browser", "Brave")
        pref = get_preference("browser")
        self.assertEqual(pref, "Brave")


if __name__ == "__main__":
    unittest.main()
