"""
Agent Skills - Plan, Execute, Verify workflow skills.
"""

from typing import List, Dict, Any
from core.skills.base import BaseSkill, SkillParameter
from core.agents import AgentWorkflow, WorkflowManager, TaskPlanner, PlanExecutor, ResultVerifier
from core.llm_provider import LLMProvider


# Global workflow manager
_workflow_manager = WorkflowManager()
_default_workflow: AgentWorkflow = None


def get_workflow_manager() -> WorkflowManager:
    global _workflow_manager
    return _workflow_manager


def get_default_workflow() -> AgentWorkflow:
    global _default_workflow
    if _default_workflow is None:
        _default_workflow = AgentWorkflow()
        _workflow_manager.register_workflow("default", _default_workflow)
    return _default_workflow


def set_workflow_llm(llm: LLMProvider) -> None:
    """Set LLM for the default workflow components."""
    workflow = get_default_workflow()
    workflow.planner.llm = llm
    workflow.verifier.llm = llm
    workflow.executor.llm_provider = llm


class AgentPlanSkill(BaseSkill):
    """Create an execution plan for a goal."""
    
    @property
    def name(self) -> str:
        return "agent.plan"
    
    @property
    def description(self) -> str:
        return "Create a step-by-step execution plan for a goal"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="goal",
                type="string",
                description="The goal to create a plan for",
                required=True,
            ),
            SkillParameter(
                name="context",
                type="object",
                description="Additional context for planning",
                required=False,
                default={},
            ),
            SkillParameter(
                name="workflow",
                type="string",
                description="Workflow name to use (default: 'default')",
                required=False,
                default="default",
            ),
        ]
    
    @property
    def category(self) -> str:
        return "agent"
    
    @property
    def examples(self) -> List[str]:
        return [
            "Plan: open notepad and type hello",
            "Create plan to play youtube video",
            "Plan to search web and save results",
        ]
    
    def execute(self, goal: str, context: Dict = None, workflow: str = "default") -> str:
        try:
            manager = get_workflow_manager()
            wf = manager.get_workflow(workflow)
            if not wf:
                wf = get_default_workflow()
            
            plan = wf.planner.create_plan(goal, context or {})
            
            lines = [f"Plan created for: {goal}", f"Plan ID: {plan.id}", f"Steps ({len(plan.steps)}):"]
            for i, step in enumerate(plan.steps, 1):
                deps = f" (depends on: {', '.join(step.depends_on)})" if step.depends_on else ""
                lines.append(f"  {i}. {step.name}: {step.description} [{step.skill_name}]{deps}")
            
            return "\n".join(lines)
        except Exception as e:
            return f"Failed to create plan: {e}"


class AgentExecuteSkill(BaseSkill):
    """Execute an agent plan."""
    
    @property
    def name(self) -> str:
        return "agent.execute"
    
    @property
    def description(self) -> str:
        return "Execute a previously created plan"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="plan_id",
                type="string",
                description="ID of the plan to execute (or 'latest')",
                required=False,
                default="latest",
            ),
            SkillParameter(
                name="goal",
                type="string",
                description="Goal to execute directly (creates plan automatically)",
                required=False,
                default="",
            ),
            SkillParameter(
                name="context",
                type="object",
                description="Additional context for execution",
                required=False,
                default={},
            ),
            SkillParameter(
                name="workflow",
                type="string",
                description="Workflow name to use",
                required=False,
                default="default",
            ),
        ]
    
    @property
    def category(self) -> str:
        return "agent"
    
    @property
    def examples(self) -> List[str]:
        return [
            "Execute plan",
            "Run agent: open notepad and type hello",
            "Execute latest plan",
        ]
    
    def execute(self, plan_id: str = "latest", goal: str = "", context: Dict = None, workflow: str = "default") -> str:
        try:
            manager = get_workflow_manager()
            wf = manager.get_workflow(workflow)
            if not wf:
                wf = get_default_workflow()
            
            if goal:
                # Execute directly from goal
                result = wf.run(goal, context or {})
            else:
                # Execute existing plan (simplified - would need plan storage)
                return "Plan storage not yet implemented. Use 'goal' parameter to execute directly."
            
            if result.success:
                lines = [f"✓ Plan executed successfully in {result.execution_time:.1f}s"]
            else:
                lines = [f"✗ Plan failed after {result.execution_time:.1f}s"]
            
            lines.append(f"Message: {result.message}")
            
            if result.outputs:
                lines.append("Outputs:")
                for step_id, output in result.outputs.items():
                    if step_id.startswith("_"):
                        continue
                    lines.append(f"  {step_id}: {str(output)[:100]}")
            
            if result.errors:
                lines.append("Errors:")
                for err in result.errors:
                    lines.append(f"  - {err}")
            
            return "\n".join(lines)
        except Exception as e:
            return f"Execution failed: {e}"


class AgentVerifySkill(BaseSkill):
    """Verify execution results."""
    
    @property
    def name(self) -> str:
        return "agent.verify"
    
    @property
    def description(self) -> str:
        return "Verify if a plan execution achieved its goal"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="plan_id",
                type="string",
                description="Plan ID to verify",
                required=True,
            ),
            SkillParameter(
                name="goal",
                type="string",
                description="Original goal for verification",
                required=False,
                default="",
            ),
        ]
    
    @property
    def category(self) -> str:
        return "agent"
    
    @property
    def examples(self) -> List[str]:
        return [
            "Verify plan execution",
            "Check if goal was achieved",
        ]
    
    def execute(self, plan_id: str, goal: str = "") -> str:
        return f"Verification for plan {plan_id} - requires plan storage implementation"


class AgentRunSkill(BaseSkill):
    """Run full agent workflow: plan -> execute -> verify."""
    
    @property
    def name(self) -> str:
        return "agent.run"
    
    @property
    def description(self) -> str:
        return "Run complete agent workflow (plan + execute + verify) for a goal"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="goal",
                type="string",
                description="Goal to achieve",
                required=True,
            ),
            SkillParameter(
                name="context",
                type="object",
                description="Additional context",
                required=False,
                default={},
            ),
            SkillParameter(
                name="workflow",
                type="string",
                description="Workflow name to use",
                required=False,
                default="default",
            ),
            SkillParameter(
                name="max_retries",
                type="number",
                description="Max retry attempts on failure",
                required=False,
                default=2,
            ),
        ]
    
    @property
    def category(self) -> str:
        return "agent"
    
    @property
    def examples(self) -> List[str]:
        return [
            "Run agent: open notepad and type hello world",
            "Agent: search for python tutorials and open first result",
            "Run agent workflow to play music on youtube",
        ]
    
    def execute(self, goal: str, context: Dict = None, workflow: str = "default", max_retries: int = 2) -> str:
        try:
            manager = get_workflow_manager()
            wf = manager.get_workflow(workflow)
            if not wf:
                wf = get_default_workflow()
                manager.register_workflow(workflow, wf)
            
            wf.max_retries = max_retries
            
            result = wf.run(goal, context or {})
            
            if result.success:
                lines = [f"✓ Agent completed: {goal}", f"Time: {result.execution_time:.1f}s"]
            else:
                lines = [f"✗ Agent failed: {goal}", f"Time: {result.execution_time:.1f}s"]
            
            lines.append(f"Message: {result.message}")
            
            if result.outputs:
                lines.append("Step Results:")
                for step_id, output in result.outputs.items():
                    if step_id.startswith("_"):
                        continue
                    lines.append(f"  {step_id}: {str(output)[:150]}")
            
            if result.errors:
                lines.append("Errors:")
                for err in result.errors:
                    lines.append(f"  - {err}")
            
            return "\n".join(lines)
        except Exception as e:
            return f"Agent run failed: {e}"


class AgentStatusSkill(BaseSkill):
    """Get agent workflow status."""
    
    @property
    def name(self) -> str:
        return "agent.status"
    
    @property
    def description(self) -> str:
        return "Get status of agent workflows"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="workflow",
                type="string",
                description="Workflow name (default: 'default')",
                required=False,
                default="default",
            ),
        ]
    
    @property
    def category(self) -> str:
        return "agent"
    
    @property
    def examples(self) -> List[str]:
        return [
            "Agent status",
            "Show workflow status",
        ]
    
    def execute(self, workflow: str = "default") -> str:
        manager = get_workflow_manager()
        workflows = manager.list_workflows()
        
        lines = ["Agent Workflows:"]
        for wf_name in workflows:
            wf = manager.get_workflow(wf_name)
            active = " (ACTIVE)" if wf_name in manager.active_workflows else ""
            lines.append(f"  {wf_name}{active}")
        
        if not workflows:
            lines.append("  No workflows registered")
        
        return "\n".join(lines)


class AgentListWorkflowsSkill(BaseSkill):
    """List available workflows."""
    
    @property
    def name(self) -> str:
        return "agent.list_workflows"
    
    @property
    def description(self) -> str:
        return "List all registered agent workflows"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return []
    
    @property
    def category(self) -> str:
        return "agent"
    
    @property
    def examples(self) -> List[str]:
        return [
            "List agent workflows",
        ]
    
    def execute(self) -> str:
        manager = get_workflow_manager()
        workflows = manager.list_workflows()
        
        if not workflows:
            return "No workflows registered"
        
        lines = ["Available Workflows:"]
        for wf_name in workflows:
            lines.append(f"  - {wf_name}")
        
        return "\n".join(lines)


def register_agent_skills(registry) -> None:
    """Register all agent skills."""
    skills = [
        AgentPlanSkill(),
        AgentExecuteSkill(),
        AgentVerifySkill(),
        AgentRunSkill(),
        AgentStatusSkill(),
        AgentListWorkflowsSkill(),
    ]
    
    for skill in skills:
        registry.register(skill.to_definition())