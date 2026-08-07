"""
Plan Executor - Executes agent plans step by step.
"""

from typing import Dict, Any, Optional, Callable
from core.intent.registry import SkillRegistry, get_registry
from core.intent.executor import IntentExecutor
from core.agents.base import AgentPlan, AgentStep, AgentStatus, AgentResult
from core.llm_provider import LLMProvider
import time
from datetime import datetime


class PlanExecutor:
    """Executes a plan step by step using the skill registry."""
    
    def __init__(
        self,
        registry: Optional[SkillRegistry] = None,
        intent_executor: Optional[IntentExecutor] = None,
        llm_provider: Optional[LLMProvider] = None,
        persona: str = "zoya",
    ):
        self.registry = registry or get_registry()
        self.intent_executor = intent_executor
        self.llm_provider = llm_provider
        self.persona = persona
        
        # Callbacks
        self.on_step_start: Optional[Callable[[AgentStep], None]] = None
        self.on_step_complete: Optional[Callable[[AgentStep], None]] = None
        self.on_step_failed: Optional[Callable[[AgentStep, str], None]] = None
    
    def execute(self, plan: AgentPlan) -> AgentResult:
        """Execute all steps in the plan."""
        start_time = time.time()
        outputs = {}
        errors = []
        
        while True:
            ready_steps = plan.get_ready_steps()
            
            if not ready_steps:
                if plan.is_complete():
                    break
                if plan.has_failed():
                    break
                # No ready steps but not complete - might be circular dependency
                errors.append("No ready steps available (possible circular dependency)")
                break
            
            # Execute ready steps (could be parallelized in future)
            for step in ready_steps:
                step_start = time.time()
                step.status = AgentStatus.EXECUTING
                step.start_time = datetime.now()
                
                if self.on_step_start:
                    self.on_step_start(step)
                
                try:
                    result = self._execute_step(step, outputs)
                    step.result = result
                    step.status = AgentStatus.COMPLETED
                    step.end_time = datetime.now()
                    outputs[step.id] = result
                    
                    if self.on_step_complete:
                        self.on_step_complete(step)
                        
                except Exception as e:
                    step.status = AgentStatus.FAILED
                    step.error = str(e)
                    step.end_time = datetime.now()
                    errors.append(f"Step '{step.name}' ({step.id}): {e}")
                    
                    if self.on_step_failed:
                        self.on_step_failed(step, str(e))
        
        execution_time = time.time() - start_time
        success = plan.is_complete() and not errors
        
        return AgentResult(
            plan_id=plan.id,
            success=success,
            message="Plan executed successfully" if success else f"Plan failed with {len(errors)} errors",
            outputs=outputs,
            errors=errors,
            execution_time=execution_time,
        )
    
    def _execute_step(self, step: AgentStep, previous_outputs: Dict[str, Any]) -> Any:
        """Execute a single step using the skill registry."""
        # Resolve parameter references from previous outputs
        resolved_params = self._resolve_parameters(step.parameters, previous_outputs)
        
        skill = self.registry.get_skill(step.skill_name)
        if not skill:
            raise ValueError(f"Skill not found: {step.skill_name}")
        
        # Execute skill - handle both SkillDefinition and direct skill instances
        if hasattr(skill, 'handler'):
            # SkillDefinition with handler
            return skill.handler(**resolved_params)
        elif hasattr(skill, 'execute'):
            return skill.execute(**resolved_params)
        elif callable(skill):
            return skill(**resolved_params)
        else:
            raise ValueError(f"Skill {step.skill_name} is not executable")
    
    def _resolve_parameters(
        self,
        parameters: Dict[str, Any],
        previous_outputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Resolve parameter references like {{step_id.output_field}}."""
        import re
        
        resolved = {}
        for key, value in parameters.items():
            if isinstance(value, str):
                # Replace {{step_id.field}} patterns
                def replace_ref(match):
                    ref = match.group(1)
                    if '.' in ref:
                        step_id, field = ref.split('.', 1)
                        if step_id in previous_outputs:
                            output = previous_outputs[step_id]
                            if isinstance(output, dict):
                                return str(output.get(field, f"{{{{{ref}}}}}"))
                            return str(output)
                    return f"{{{{{ref}}}}}"
                
                resolved[key] = re.sub(r'\{\{(\w+\.\w+)\}\}', replace_ref, value)
            else:
                resolved[key] = value
        
        return resolved
    
    def execute_step(self, step: AgentStep, previous_outputs: Dict[str, Any] = None) -> Any:
        """Execute a single step (useful for manual/stepwise execution)."""
        previous_outputs = previous_outputs or {}
        return self._execute_step(step, previous_outputs)