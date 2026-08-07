"""
Multi-Agent Orchestrator - High-level orchestration for multi-agent workflows.
"""

from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import uuid
import time
import threading

from core.multiagent.base import (
    BaseAgent, AgentConfig, AgentRole, AgentMessage, MessageType,
    AgentMessageBus, SharedState, AgentPlan, AgentStep, AgentStatus, AgentResult,
)
from core.multiagent.agents import (
    ResearcherAgent, PlannerAgent, ExecutorAgent, VerifierAgent,
    CoordinatorAgent, CriticAgent, SummarizerAgent, create_default_team,
)
from core.llm_provider import LLMProvider
from core.intent.registry import SkillRegistry, get_registry


class WorkflowPattern(Enum):
    """Predefined multi-agent workflow patterns."""
    RESEARCH_PLAN_EXECUTE_VERIFY = "research_plan_execute_verify"
    PLAN_EXECUTE_VERIFY = "plan_execute_verify"
    PARALLEL_RESEARCH = "parallel_research"
    DEBATE = "debate"  # Multiple agents debate a topic
    PIPELINE = "pipeline"  # Sequential pipeline
    MAP_REDUCE = "map_reduce"  # Parallel execution with aggregation


@dataclass
class WorkflowStep:
    """A step in a multi-agent workflow."""
    name: str
    agent_role: AgentRole
    task_template: str  # Template with {goal}, {context}, {previous_results}
    depends_on: List[str] = field(default_factory=list)
    timeout: float = 60.0
    required: bool = True


@dataclass
class MultiAgentWorkflow:
    """A multi-agent workflow definition."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    pattern: WorkflowPattern = WorkflowPattern.RESEARCH_PLAN_EXECUTE_VERIFY
    steps: List[WorkflowStep] = field(default_factory=list)
    goal: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class MultiAgentOrchestrator:
    """Orchestrates multi-agent workflows."""
    
    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
        registry: Optional[SkillRegistry] = None,
    ):
        self.llm_provider = llm_provider
        self.registry = registry or get_registry()
        
        # Create default team
        self.team = create_default_team(llm_provider, self.registry)
        self.message_bus = self.team[AgentRole.COORDINATOR].message_bus
        self.shared_state = self.team[AgentRole.COORDINATOR].shared_state
        self.coordinator = self.team[AgentRole.COORDINATOR]
        
        # Workflow registry
        self.workflows: Dict[str, MultiAgentWorkflow] = {}
        self.active_workflows: Dict[str, Dict[str, Any]] = {}
        
        # Register built-in workflows
        self._register_builtin_workflows()
        
        # Callbacks
        self.on_workflow_start: Optional[Callable[[str], None]] = None
        self.on_workflow_step: Optional[Callable[[str, str, Dict[str, Any]], None]] = None
        self.on_workflow_complete: Optional[Callable[[str, Dict[str, Any]], None]] = None
        self.on_workflow_failed: Optional[Callable[[str, str], None]] = None
    
    def _register_builtin_workflows(self) -> None:
        """Register built-in workflow patterns."""
        
        # Research -> Plan -> Execute -> Verify
        self.register_workflow(MultiAgentWorkflow(
            name="research_plan_execute_verify",
            description="Full cycle: research, plan, execute, verify",
            pattern=WorkflowPattern.RESEARCH_PLAN_EXECUTE_VERIFY,
            steps=[
                WorkflowStep(
                    name="research",
                    agent_role=AgentRole.RESEARCHER,
                    task_template="Research: {goal}",
                ),
                WorkflowStep(
                    name="plan",
                    agent_role=AgentRole.PLANNER,
                    task_template="Create plan for: {goal}",
                    depends_on=["research"],
                ),
                WorkflowStep(
                    name="execute",
                    agent_role=AgentRole.EXECUTOR,
                    task_template="Execute plan for: {goal}",
                    depends_on=["plan"],
                ),
                WorkflowStep(
                    name="verify",
                    agent_role=AgentRole.VERIFIER,
                    task_template="Verify result for: {goal}",
                    depends_on=["execute"],
                ),
            ],
        ))
        
        # Plan -> Execute -> Verify (simpler)
        self.register_workflow(MultiAgentWorkflow(
            name="plan_execute_verify",
            description="Plan, execute, verify without research",
            pattern=WorkflowPattern.PLAN_EXECUTE_VERIFY,
            steps=[
                WorkflowStep(
                    name="plan",
                    agent_role=AgentRole.PLANNER,
                    task_template="Create plan for: {goal}",
                ),
                WorkflowStep(
                    name="execute",
                    agent_role=AgentRole.EXECUTOR,
                    task_template="Execute plan for: {goal}",
                    depends_on=["plan"],
                ),
                WorkflowStep(
                    name="verify",
                    agent_role=AgentRole.VERIFIER,
                    task_template="Verify result for: {goal}",
                    depends_on=["execute"],
                ),
            ],
        ))
        
        # Parallel research from multiple angles
        self.register_workflow(MultiAgentWorkflow(
            name="parallel_research",
            description="Parallel research from multiple agents",
            pattern=WorkflowPattern.PARALLEL_RESEARCH,
            steps=[
                WorkflowStep(
                    name="research_web",
                    agent_role=AgentRole.RESEARCHER,
                    task_template="Research web for: {goal}",
                ),
                WorkflowStep(
                    name="research_memory",
                    agent_role=AgentRole.RESEARCHER,
                    task_template="Search memory for: {goal}",
                ),
                WorkflowStep(
                    name="synthesize",
                    agent_role=AgentRole.SUMMARIZER,
                    task_template="Synthesize research results for: {goal}",
                    depends_on=["research_web", "research_memory"],
                ),
            ],
        ))
        
        # Debate pattern - multiple agents give opinions
        self.register_workflow(MultiAgentWorkflow(
            name="debate",
            description="Multiple agents debate a topic",
            pattern=WorkflowPattern.DEBATE,
            steps=[
                WorkflowStep(
                    name="pro_arguments",
                    agent_role=AgentRole.RESEARCHER,
                    task_template="Find arguments supporting: {goal}",
                ),
                WorkflowStep(
                    name="con_arguments",
                    agent_role=AgentRole.CRITIC,
                    task_template="Find arguments against: {goal}",
                ),
                WorkflowStep(
                    name="synthesize",
                    agent_role=AgentRole.SUMMARIZER,
                    task_template="Synthesize debate on: {goal}",
                    depends_on=["pro_arguments", "con_arguments"],
                ),
            ],
        ))
    
    def register_workflow(self, workflow: MultiAgentWorkflow) -> None:
        """Register a workflow."""
        self.workflows[workflow.name] = workflow
    
    def get_workflow(self, name: str) -> Optional[MultiAgentWorkflow]:
        """Get a workflow by name."""
        return self.workflows.get(name)
    
    def list_workflows(self) -> List[str]:
        """List available workflows."""
        return list(self.workflows.keys())
    
    def run_workflow(
        self,
        workflow_name: str,
        goal: str,
        context: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """Run a multi-agent workflow."""
        workflow = self.get_workflow(workflow_name)
        if not workflow:
            return {"error": f"Workflow {workflow_name} not found"}
        
        workflow_id = str(uuid.uuid4())
        context = context or {}
        context["goal"] = goal
        
        self.active_workflows[workflow_id] = {
            "workflow": workflow,
            "goal": goal,
            "context": context,
            "results": {},
            "status": "running",
            "start_time": time.time(),
        }
        
        if self.on_workflow_start:
            self.on_workflow_start(workflow_id)
        
        try:
            results = self._execute_workflow(workflow, workflow_id, goal, context)
            
            self.active_workflows[workflow_id]["status"] = "completed"
            self.active_workflows[workflow_id]["results"] = results
            self.active_workflows[workflow_id]["end_time"] = time.time()
            
            if self.on_workflow_complete:
                self.on_workflow_complete(workflow_id, results)
            
            return {"workflow_id": workflow_id, "goal": goal, "results": results}
            
        except Exception as e:
            self.active_workflows[workflow_id]["status"] = "failed"
            self.active_workflows[workflow_id]["error"] = str(e)
            
            if self.on_workflow_failed:
                self.on_workflow_failed(workflow_id, str(e))
            
            return {"workflow_id": workflow_id, "goal": goal, "error": str(e)}
    
    def _execute_workflow(
        self,
        workflow: MultiAgentWorkflow,
        workflow_id: str,
        goal: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute a workflow step by step."""
        results = {}
        completed_steps = set()
        
        # Build dependency graph
        step_map = {step.name: step for step in workflow.steps}
        
        while len(completed_steps) < len(workflow.steps):
            # Find ready steps
            ready = []
            for step in workflow.steps:
                if step.name in completed_steps:
                    continue
                if all(dep in completed_steps for dep in step.depends_on):
                    ready.append(step)
            
            if not ready:
                # Circular dependency or missing dependency
                remaining = [s.name for s in workflow.steps if s.name not in completed_steps]
                raise RuntimeError(f"Cannot proceed: remaining steps {remaining} have unmet dependencies")
            
            # Execute ready steps (can be parallelized in future)
            for step in ready:
                agent = self.team.get(step.agent_role)
                if not agent:
                    if step.required:
                        raise RuntimeError(f"Required agent {step.agent_role.value} not available")
                    results[step.name] = {"error": f"Agent {step.agent_role.value} not available"}
                    completed_steps.add(step.name)
                    continue
                
                # Prepare task with template substitution
                task = step.task_template.format(
                    goal=goal,
                    context=context,
                    previous_results=results,
                )
                
                step_context = context.copy()
                step_context.update(results)
                
                # Special handling: if previous step was a planner, extract the plan
                for dep in step.depends_on:
                    if dep in results and isinstance(results[dep], dict) and "plan" in results[dep]:
                        # Planner result has nested plan structure
                        step_context["plan"] = results[dep]["plan"]
                    if dep in results and isinstance(results[dep], dict) and "success" in results[dep]:
                        # Executor result has success/outputs
                        step_context["result"] = results[dep]
                
                # Always pass the goal for verification
                step_context["goal"] = goal
                
                if self.on_workflow_step:
                    self.on_workflow_step(workflow_id, step.name, {"task": task, "agent": step.agent_role.value})
                
                # Send task request
                response = self.message_bus.request_response(
                    sender_id=self.coordinator.agent_id,
                    sender_role=self.coordinator.role,
                    recipient_id=agent.agent_id,
                    message_type=MessageType.TASK_REQUEST,
                    content={"task": task, "context": step_context},
                    timeout=step.timeout,
                )
                
                if response:
                    if response.message_type == MessageType.TASK_RESPONSE:
                        result = response.content.get("result")
                        results[step.name] = result
                        
                        if self.on_workflow_step:
                            self.on_workflow_step(workflow_id, step.name, {"result": result, "status": "completed"})
                    elif response.message_type == MessageType.ERROR:
                        error = response.content.get("error")
                        results[step.name] = {"error": error}
                        
                        if self.on_workflow_step:
                            self.on_workflow_step(workflow_id, step.name, {"error": error, "status": "failed"})
                        
                        if step.required:
                            raise RuntimeError(f"Required step {step.name} failed: {error}")
                else:
                    results[step.name] = {"error": "Timeout or no response"}
                    if step.required:
                        raise RuntimeError(f"Required step {step.name} timed out")
                
                completed_steps.add(step.name)
        
        return results
    
    def run_custom_workflow(
        self,
        goal: str,
        steps: List[Dict[str, Any]],
        context: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """Run a custom workflow defined by steps."""
        workflow = MultiAgentWorkflow(
            name=f"custom_{uuid.uuid4().hex[:8]}",
            description="Custom workflow",
            steps=[
                WorkflowStep(
                    name=s["name"],
                    agent_role=AgentRole(s["agent_role"]),
                    task_template=s["task_template"],
                    depends_on=s.get("depends_on", []),
                    timeout=s.get("timeout", 60.0),
                    required=s.get("required", True),
                )
                for s in steps
            ],
            goal=goal,
        )
        
        workflow_id = str(uuid.uuid4())
        self.active_workflows[workflow_id] = {
            "workflow": workflow,
            "goal": goal,
            "context": context or {},
            "results": {},
            "status": "running",
        }
        
        return self._execute_workflow(workflow, workflow_id, goal, context or {})
    
    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a workflow."""
        return self.active_workflows.get(workflow_id)
    
    def get_team_status(self) -> Dict[str, Any]:
        """Get status of all team members."""
        return self.coordinator._get_team_status()
    
    def add_agent(self, agent: BaseAgent) -> None:
        """Add a custom agent to the team."""
        self.team[agent.role] = agent
        self.message_bus.register_agent(agent)
        self.coordinator.register_team_member(agent)
    
    def remove_agent(self, role: AgentRole) -> bool:
        """Remove an agent from the team."""
        if role in self.team:
            self.message_bus.unregister_agent(self.team[role].agent_id)
            del self.team[role]
            return True
        return False


# Convenience function
def create_orchestrator(
    llm_provider: Optional[LLMProvider] = None,
    registry: Optional[SkillRegistry] = None,
) -> MultiAgentOrchestrator:
    """Create a multi-agent orchestrator with default team."""
    return MultiAgentOrchestrator(llm_provider, registry)