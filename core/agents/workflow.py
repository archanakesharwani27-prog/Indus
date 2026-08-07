"""
Agent Workflow Orchestrator - Coordinates plan, execute, verify cycles.
"""

from typing import Dict, Any, Optional, List, Callable
from core.agents.base import Agent, AgentPlan, AgentResult, AgentStep, AgentStatus
from core.agents.planner import TaskPlanner
from core.agents.executor import PlanExecutor
from core.agents.verifier import ResultVerifier
import time


class AgentWorkflow:
    """Orchestrates the full agent workflow: Plan -> Execute -> Verify."""
    
    def __init__(
        self,
        planner: Optional[TaskPlanner] = None,
        executor: Optional[PlanExecutor] = None,
        verifier: Optional[ResultVerifier] = None,
        max_retries: int = 2,
        retry_on_failure: bool = True,
    ):
        self.planner = planner or TaskPlanner()
        self.executor = executor or PlanExecutor()
        self.verifier = verifier or ResultVerifier()
        self.max_retries = max_retries
        self.retry_on_failure = retry_on_failure
        
        # Callbacks for progress tracking
        self.on_step_start: Optional[Callable[[AgentStep], None]] = None
        self.on_step_complete: Optional[Callable[[AgentStep], None]] = None
        self.on_step_failed: Optional[Callable[[AgentStep, str], None]] = None
        self.on_plan_complete: Optional[Callable[[AgentPlan, AgentResult], None]] = None
    
    def run(
        self,
        goal: str,
        context: Dict[str, Any] = None,
        plan: Optional[AgentPlan] = None,
    ) -> AgentResult:
        """Execute full workflow for a goal."""
        start_time = time.time()
        
        if plan is None:
            plan = self.planner.create_plan(goal, context)
        
        plan.status = AgentStatus.EXECUTING
        
        for attempt in range(self.max_retries + 1):
            if attempt > 0:
                plan.status = AgentStatus.EXECUTING
            
            result = self.executor.execute(plan)
            
            if result.success or not self.retry_on_failure:
                break
            
            # Retry: reset failed steps and try again
            for step in plan.steps:
                if step.status == AgentStatus.FAILED:
                    step.status = AgentStatus.PENDING
                    step.error = None
                    step.result = None
        
        # Verify
        plan.status = AgentStatus.VERIFYING
        result = self.verifier.verify(plan, result)
        
        execution_time = time.time() - start_time
        result.execution_time = execution_time
        
        plan.status = AgentStatus.COMPLETED if result.success else AgentStatus.FAILED
        
        if self.on_plan_complete:
            self.on_plan_complete(plan, result)
        
        return result
    
    def run_async(
        self,
        goal: str,
        context: Dict[str, Any] = None,
        plan: Optional[AgentPlan] = None,
        callback: Optional[Callable[[AgentResult], None]] = None,
    ):
        """Run workflow asynchronously (placeholder for future async support)."""
        import threading
        
        def _run():
            result = self.run(goal, context, plan)
            if callback:
                callback(result)
        
        thread = threading.Thread(target=_run)
        thread.start()
        return thread


class WorkflowManager:
    """Manages multiple agent workflows."""
    
    def __init__(self):
        self.workflows: Dict[str, AgentWorkflow] = {}
        self.active_workflows: Dict[str, AgentWorkflow] = {}
    
    def register_workflow(self, name: str, workflow: AgentWorkflow) -> None:
        self.workflows[name] = workflow
    
    def get_workflow(self, name: str) -> Optional[AgentWorkflow]:
        return self.workflows.get(name)
    
    def run_workflow(
        self,
        workflow_name: str,
        goal: str,
        context: Dict[str, Any] = None,
    ) -> Optional[AgentResult]:
        workflow = self.get_workflow(workflow_name)
        if not workflow:
            return None
        
        self.active_workflows[workflow_name] = workflow
        try:
            return workflow.run(goal, context)
        finally:
            self.active_workflows.pop(workflow_name, None)
    
    def list_workflows(self) -> List[str]:
        return list(self.workflows.keys())