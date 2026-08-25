# agent/agent_loop.py
"""
INDUS Unified Closed-Loop Agent Execution Loop
Orchestrates goal understanding, validated plan generation, step-by-step verified execution,
failure diagnosis, safe retries/replanning, memory integration, and cooperative cancellation.
"""

import json
import logging
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from agent.task_model import AgentTask, TaskStep, TaskStatus, ErrorCategory, agent_context
from agent.planner import create_agent_plan, replan_remaining_steps
from agent.error_handler import classify_error, generate_alternative_step, is_destructive_step
from actions.action_verifier import ActionVerifier
from core.cancellation import cancellation_manager
from core.security_vault import security_vault

logger = logging.getLogger("IndusAgentLoop")

# Direct conversational questions that do not require tool planning
DIRECT_CONVERSATION_PATTERNS = [
    r"^(hi|hello|hey|namaste|kem cho|good morning|good evening)\b",
    r"^(who made you|who are you|what is your name|tumhe kisne banaya|aap kaun ho)\b",
    r"^(tell me a joke|sing a song|say something funny|ek joke sunao)\b",
    r"^(how are you|kaise ho|kaisi ho|kya chal raha hai)\b",
    r"^(what can you do|tum kya kar sakti ho|help me with features)\b",
]


def is_direct_chat_query(goal: str) -> bool:
    """Detect if request is purely conversational with no computer actions required."""
    import re
    g_lower = goal.strip().lower()
    return any(re.search(p, g_lower) for p in DIRECT_CONVERSATION_PATTERNS)


class ClosedLoopAgent:
    """
    Unified Agent Execution Engine for INDUS.
    Converts complex user goals into closed-loop verified computer actions.
    """

    def __init__(self):
        self.current_task: Optional[AgentTask] = None

    def execute_goal(
        self,
        goal: str,
        player_ui=None,
        speak: Optional[Callable[[str], None]] = None,
        timeout_seconds: float = 60.0,
    ) -> str:
        """
        Main entry point for autonomous goal execution.
        """
        if not goal or not goal.strip():
            return "Please provide a goal or task to execute."

        goal = goal.strip()

        # Check cancellation
        if cancellation_manager.is_cancelled():
            return "Task execution was cancelled by user."


        # Step 1: Direct conversational queries bypass tool planning
        if is_direct_chat_query(goal):
            if player_ui:
                player_ui.set_state("SPEAKING")
            ans = self._execute_direct_chat(goal)
            agent_context.update_context(output=ans)
            if player_ui:
                player_ui.set_state("LISTENING")
            return ans

        # Step 2: Initialize Task & UI State
        task = AgentTask.create(goal=goal, timeout_seconds=timeout_seconds)
        self.current_task = task
        task.status = TaskStatus.PLANNING

        if player_ui:
            player_ui.set_state("PLANNING")
            player_ui.write_log(f"• SYS: [Planner] Analyzing goal: '{goal}'")

        if speak:
            speak(f"Planning steps for {goal[:40]}...")

        # Step 3: Plan Generation
        try:
            steps = create_agent_plan(goal)
            task.steps = steps
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            if player_ui:
                player_ui.set_state("FAILED")
            return f"Failed to generate execution plan: {e}"

        if not task.steps:
            task.status = TaskStatus.FAILED
            return "No valid execution steps could be determined for this goal."

        if player_ui:
            step_summary = " -> ".join(f"[{s.tool}]" for s in task.steps)
            player_ui.write_log(f"• SYS: [Plan Generated] {len(task.steps)} steps: {step_summary}")

        verifier = ActionVerifier(player_ui=player_ui)

        # Step 4: Step-by-Step Execution Loop
        task.status = TaskStatus.EXECUTING
        current_idx = 0

        while current_idx < len(task.steps):
            if task.is_cancelled():
                task.status = TaskStatus.CANCELLED
                if player_ui:
                    player_ui.set_state("CANCELLED")
                    player_ui.write_log("• SYS: [Agent] Task cancelled by user.")
                return "Task execution was cancelled by user."

            if task.is_timed_out():
                task.status = TaskStatus.FAILED
                task.error_message = f"Task timed out after {timeout_seconds:.0f} seconds."
                if player_ui:
                    player_ui.set_state("FAILED")
                return f"Task timed out after {timeout_seconds:.0f} seconds."

            step = task.steps[current_idx]
            task.current_step_idx = current_idx
            step.status = "running"

            if player_ui:
                player_ui.set_state("EXECUTING")
                player_ui.write_log(f"• SYS: [Step {current_idx + 1}/{len(task.steps)}] {step.description}")

            # Security Policy Check
            sec_decision = security_vault.evaluate_action(
                action_name=step.tool,
                parameters=step.parameters,
            )
            if not sec_decision.allowed:
                step.status = "failed"
                task.status = TaskStatus.FAILED
                err_msg = f"Security Policy Blocked step [{step.tool}]: {sec_decision.reason}"
                if player_ui:
                    player_ui.write_log(f"• SYS: [Security] {err_msg}")
                return err_msg

            # Capture pre-action state snapshot
            pre_snap = verifier.capture_state_snapshot(step.tool, step.parameters)

            # Execute tool action
            tool_result, tool_err = self._dispatch_tool_action(step.tool, step.parameters, player_ui)

            if task.is_cancelled():
                task.status = TaskStatus.CANCELLED
                return "Task execution cancelled."

            # Capture post-action state snapshot & verify
            if player_ui:
                player_ui.set_state("VERIFYING")

            post_snap = verifier.capture_state_snapshot(step.tool, step.parameters)
            v_res = verifier.verify_action_success(
                action_name=step.tool,
                pre_snapshot=pre_snap,
                post_snapshot=post_snap,
                expected_target=step.description,
            )

            # Evaluate Step Outcome
            is_success = (tool_err is None) and (v_res.verified or v_res.status == "SUCCESS")

            if is_success:
                step.status = "success"
                step.result = tool_result
                step.verification_details = v_res.details
                task.completed_steps.append({
                    "step_id": step.step_id,
                    "tool": step.tool,
                    "description": step.description,
                    "result": str(tool_result)[:100],
                })

                # Update context
                agent_context.update_context(
                    app=step.parameters.get("app_name", ""),
                    target=step.parameters.get("target") or step.parameters.get("query", ""),
                    action=step.tool,
                    output=str(tool_result)[:100],
                )

                if player_ui:
                    player_ui.write_log(f"• SYS: [Step {current_idx + 1} Verified] {v_res.details}")

                current_idx += 1

            else:
                # Failure Recovery & Diagnosis
                failure_msg = tool_err or v_res.details or "Action did not produce expected outcome."
                step.retries += 1
                task.retry_count += 1
                category, reason, alt_suggestion = classify_error(step, failure_msg, attempt=step.retries)

                if player_ui:
                    player_ui.set_state("RECOVERING")
                    player_ui.write_log(f"• SYS: [Recovery] Step failed ({category.value}): {reason}")

                if category == ErrorCategory.SECURITY_DENIAL or is_destructive_step(step):
                    task.status = TaskStatus.FAILED
                    return f"Task stopped: {reason}"

                if category == ErrorCategory.TRANSIENT and step.retries <= step.max_retries:
                    # Safe transient retry
                    time.sleep(0.4)
                    continue

                # Try generating alternative step strategy
                alt_step = generate_alternative_step(step, category, alt_suggestion)
                if alt_step and alt_step.executed_strategy != step.executed_strategy:
                    if player_ui:
                        player_ui.write_log(f"• SYS: [Alternative Strategy] Switching to: {alt_step.description}")
                    task.steps[current_idx] = alt_step
                    continue

                # Re-plan remaining steps
                if task.replan_count < task.max_replans:
                    task.replan_count += 1
                    if player_ui:
                        player_ui.write_log(f"• SYS: [Re-planning] Adjusting remaining steps (replan {task.replan_count}/{task.max_replans})")
                    # Publish replan event to EventBus
                    try:
                        from core.event_bus import event_bus, E
                        event_bus.publish(E.REPLAN_STARTED, source="agent_loop",
                                          data={"replan_count": task.replan_count,
                                                "failed_tool": step.tool,
                                                "reason": failure_msg[:100]})
                    except Exception:
                        pass
                    revised = replan_remaining_steps(
                        goal=task.current_goal,
                        completed_steps=task.completed_steps,
                        failed_step=step,
                        error_reason=failure_msg,
                        alternative_strategy=alt_suggestion,
                    )
                    if revised:
                        task.steps = revised
                        current_idx = 0
                        continue

                # Step cannot be recovered and replan limit reached
                if step.critical:
                    task.status = TaskStatus.FAILED
                    task.error_message = failure_msg
                    if player_ui:
                        player_ui.set_state("FAILED")
                    return f"Task failed at step [{step.tool}]: {failure_msg}"
                else:
                    # Non-critical step skipped
                    step.status = "skipped"
                    current_idx += 1

        # Step 5: Task Completed
        task.status = TaskStatus.COMPLETED
        task.updated_at = time.time()

        # Store useful task outcomes in permanent memory
        self._record_memory_outcome(task)

        if player_ui:
            player_ui.set_state("LISTENING")
            player_ui.write_log(f"• SYS: [Task Complete] All {len(task.completed_steps)} steps verified successfully.")

        summary_msg = f"Task completed successfully. Verified {len(task.completed_steps)} actions for: '{goal}'."
        return summary_msg

    def _execute_direct_chat(self, prompt: str) -> str:
        """Handle pure conversational queries instantly."""
        from agent.planner import _get_api_key, CANDIDATE_MODELS
        api_key = _get_api_key()
        if api_key:
            try:
                from google import genai
                client = genai.Client(api_key=api_key, http_options={"api_version": "v1beta"})
                for m in CANDIDATE_MODELS:
                    try:
                        resp = client.models.generate_content(
                            model=m,
                            contents=prompt,
                            config={
                                "system_instruction": "You are INDUS, an intelligent AI assistant made by Ansh Kesharwani. Respond in crisp, natural Hinglish. Max 2 sentences.",
                                "temperature": 0.3,
                            },
                        )
                        if resp.text:
                            return resp.text.strip()
                    except Exception:
                        pass
            except Exception:
                pass
        return "Main aapki sahayata ke liye tayar hoon, Ansh. Aap kya karna chahte hain?"


    def _dispatch_tool_action(self, tool_name: str, parameters: dict, player_ui=None) -> Tuple[Any, Optional[str]]:
        """
        Dispatches tool call to the canonical 33-tool registry in core/tool_registry.py.
        Both this path and main.py._execute_tool() share the same registry,
        so agent_task has the same 33-tool capability surface as Gemini Live commands.
        """
        from core.tool_registry import dispatch as _registry_dispatch

        result, error = _registry_dispatch(tool_name, parameters, player=player_ui)

        # Preserve special-case failure detection for vision tools
        # (these return structured dicts or specific error strings)
        if error is None and tool_name == "vision_click":
            r_str = str(result)
            if ("Cannot click" in r_str or "not found" in r_str.lower()
                    or "ambiguous" in r_str.lower()):
                return result, r_str

        if error is None and tool_name == "vision_find_element":
            if isinstance(result, dict) and not result.get("found"):
                return result, "Target element not found on screen."

        return result, error


    def _record_memory_outcome(self, task: AgentTask):
        """Record meaningful workflow preferences in permanent memory."""
        try:
            from memory.memory_manager import record_conversation_turn, update_memory
            record_conversation_turn(
                user_text=task.original_user_request,
                indus_text=f"Completed {len(task.completed_steps)} steps.",
                intent="autonomous_goal",
            )
        except Exception as e:
            logger.debug(f"[AgentLoop] Memory record error: {e}")


# Global agent runner instance
closed_loop_agent = ClosedLoopAgent()


