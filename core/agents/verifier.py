"""
Result Verifier - Verifies execution results and determines success.
"""

from typing import Dict, Any, Optional, List, Callable
from core.llm_provider import LLMProvider
from core.agents.base import AgentPlan, AgentResult, AgentStatus, AgentStep
from core.intent.registry import SkillRegistry, get_registry
import time


class ResultVerifier:
    """Verifies agent execution results against the goal."""
    
    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
        registry: Optional[SkillRegistry] = None,
        persona: str = "zoya",
        auto_retry: bool = True,
    ):
        self.llm = llm_provider
        self.registry = registry or get_registry()
        self.persona = persona
        self.auto_retry = auto_retry
        
        # Verification rules: skill -> verification function
        self.verification_rules: Dict[str, Callable] = {}
        self._register_default_verifiers()
    
    def _register_default_verifiers(self) -> None:
        """Register default verification functions for common skills."""
        self.verification_rules.update({
            "system.open_app": self._verify_app_opened,
            "system.volume_control": self._verify_volume_changed,
            "system.screenshot": self._verify_screenshot_taken,
            "system.list_windows": self._verify_windows_listed,
            "web.open_url": self._verify_url_opened,
            "web.search": self._verify_search_completed,
            "web.youtube_play": self._verify_youtube_played,
            "memory.search": self._verify_memory_searched,
            "vision.describe_screen": self._verify_screen_described,
            "vision.find_on_screen": self._verify_found_on_screen,
        })
    
    def verify(self, plan: AgentPlan, result: AgentResult) -> AgentResult:
        """Verify the execution result."""
        if not result.success:
            # If execution failed, check if we can provide better error info
            return self._verify_failed_plan(plan, result)
        
        # If LLM available, do semantic verification
        if self.llm:
            return self._verify_with_llm(plan, result)
        
        # Otherwise, use rule-based verification
        return self._verify_with_rules(plan, result)
    
    def _verify_with_llm(self, plan: AgentPlan, result: AgentResult) -> AgentResult:
        """Use LLM to verify if goal was achieved."""
        step_results = {}
        for step in plan.steps:
            if step.id in result.outputs:
                step_results[step.name] = {
                    "skill": step.skill_name,
                    "result": result.outputs[step.id],
                    "status": step.status.value,
                }
        
        prompt = f"""Verify if this plan successfully achieved the goal.

Goal: {plan.goal}

Plan Steps and Results:
{step_results}

Errors: {result.errors}

Respond with JSON:
{{
  "success": true/false,
  "reason": "explanation",
  "missing": ["what wasn't accomplished"],
  "suggestions": ["how to improve"]
}}"""
        
        try:
            response = self.llm.chat([{"role": "user", "content": prompt}])
            import re, json
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                verification = json.loads(json_match.group())
                
                if not verification.get("success", True):
                    result.success = False
                    result.message = verification.get("reason", "Goal not fully achieved")
                    result.errors.extend(verification.get("missing", []))
                
                # Add verification metadata
                result.outputs["_verification"] = verification
        except Exception as e:
            print(f"LLM verification failed: {e}")
            return self._verify_with_rules(plan, result)
        
        return result
    
    def _verify_with_rules(self, plan: AgentPlan, result: AgentResult) -> AgentResult:
        """Rule-based verification using registered verifiers."""
        all_verified = True
        verification_errors = []
        
        for step in plan.steps:
            if step.status != AgentStatus.COMPLETED:
                continue
            
            verifier = self.verification_rules.get(step.skill_name)
            if verifier:
                try:
                    verified = verifier(step, result.outputs.get(step.id))
                    if not verified:
                        all_verified = False
                        verification_errors.append(f"Verification failed for {step.name}")
                except Exception as e:
                    all_verified = False
                    verification_errors.append(f"Verifier error for {step.name}: {e}")
        
        if not all_verified:
            result.success = False
            result.message = "Rule-based verification failed"
            result.errors.extend(verification_errors)
        
        return result
    
    def _verify_failed_plan(self, plan: AgentPlan, result: AgentResult) -> AgentResult:
        """Analyze failed plan to provide better diagnostics."""
        failed_steps = [s for s in plan.steps if s.status == AgentStatus.FAILED]
        
        if failed_steps:
            first_failed = failed_steps[0]
            result.message = f"Plan failed at step: {first_failed.name} ({first_failed.skill_name})"
            if first_failed.error:
                result.message += f" - {first_failed.error}"
        
        return result
    
    # Default verifiers
    def _verify_app_opened(self, step: AgentStep, output: Any) -> bool:
        """Verify app was opened."""
        if isinstance(output, str):
            return "opened" in output.lower() or "launched" in output.lower() or "started" in output.lower()
        return True  # Assume success if no error
    
    def _verify_volume_changed(self, step: AgentStep, output: Any) -> bool:
        """Verify volume was changed."""
        if isinstance(output, str):
            return "volume" in output.lower() and ("set" in output.lower() or "changed" in output.lower() or "muted" in output.lower())
        return True
    
    def _verify_screenshot_taken(self, step: AgentStep, output: Any) -> bool:
        """Verify screenshot was taken."""
        if isinstance(output, str):
            return "screenshot" in output.lower() and ("saved" in output.lower() or "captured" in output.lower() or ".png" in output.lower())
        return True
    
    def _verify_windows_listed(self, step: AgentStep, output: Any) -> bool:
        """Verify windows were listed."""
        if isinstance(output, str):
            return "window" in output.lower() or "found" in output.lower()
        if isinstance(output, list):
            return len(output) > 0
        return True
    
    def _verify_url_opened(self, step: AgentStep, output: Any) -> bool:
        """Verify URL was opened."""
        if isinstance(output, str):
            return "opened" in output.lower() or "navigated" in output.lower()
        return True
    
    def _verify_search_completed(self, step: AgentStep, output: Any) -> bool:
        """Verify search completed."""
        if isinstance(output, str):
            return "search" in output.lower() and ("result" in output.lower() or "found" in output.lower())
        return True
    
    def _verify_youtube_played(self, step: AgentStep, output: Any) -> bool:
        """Verify YouTube video played."""
        if isinstance(output, str):
            return "youtube" in output.lower() and ("play" in output.lower() or "opened" in output.lower())
        return True
    
    def _verify_memory_searched(self, step: AgentStep, output: Any) -> bool:
        """Verify memory was searched."""
        if isinstance(output, str):
            return "found" in output.lower() or "result" in output.lower() or "memory" in output.lower()
        return True
    
    def _verify_screen_described(self, step: AgentStep, output: Any) -> bool:
        """Verify screen was described."""
        if isinstance(output, str):
            return len(output) > 50  # Reasonable description length
        return True
    
    def _verify_found_on_screen(self, step: AgentStep, output: Any) -> bool:
        """Verify element was found on screen."""
        if isinstance(output, str):
            return "found" in output.lower() or "located" in output.lower() or "position" in output.lower()
        return True
    
    def register_verifier(self, skill_name: str, verifier: Callable) -> None:
        """Register a custom verifier for a skill."""
        self.verification_rules[skill_name] = verifier