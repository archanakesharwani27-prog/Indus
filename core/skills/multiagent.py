"""
Multi-Agent Skills - Skills for multi-agent collaboration.
"""

from typing import List, Dict, Any
from core.skills.base import BaseSkill, SkillParameter
from core.multiagent import create_orchestrator, MultiAgentOrchestrator, WorkflowPattern
from core.llm_provider import LLMProvider


# Global orchestrator instance
_orchestrator: MultiAgentOrchestrator = None


def get_orchestrator() -> MultiAgentOrchestrator:
    """Get or create the global orchestrator."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = create_orchestrator()
    return _orchestrator


def set_orchestrator_llm(llm: LLMProvider) -> None:
    """Set LLM for the orchestrator and all agents."""
    global _orchestrator
    _orchestrator = create_orchestrator(llm_provider=llm)


class MultiAgentRunWorkflowSkill(BaseSkill):
    """Run a multi-agent workflow."""
    
    @property
    def name(self) -> str:
        return "multiagent.run_workflow"
    
    @property
    def description(self) -> str:
        return "Run a multi-agent workflow (research_plan_execute_verify, plan_execute_verify, parallel_research, debate)"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="workflow",
                type="string",
                description="Workflow name to run",
                required=True,
            ),
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
        ]
    
    @property
    def category(self) -> str:
        return "multiagent"
    
    @property
    def examples(self) -> List[str]:
        return [
            "Run multiagent workflow research_plan_execute_verify: plan a trip to Japan",
            "Multiagent: plan_execute_verify to open notepad and type hello",
            "Run parallel_research on python async programming",
            "Start debate on: should I use Rust or Go",
        ]
    
    def execute(self, workflow: str, goal: str, context: Dict = None) -> str:
        try:
            orchestrator = get_orchestrator()
            result = orchestrator.run_workflow(workflow, goal, context or {})
            
            if "error" in result:
                return f"✗ Workflow failed: {result['error']}"
            
            lines = [f"✓ Multi-agent workflow completed: {workflow}"]
            lines.append(f"Goal: {goal}")
            lines.append(f"Workflow ID: {result['workflow_id']}")
            lines.append("")
            lines.append("Results:")
            
            for step_name, step_result in result.get("results", {}).items():
                lines.append(f"  {step_name}:")
                if isinstance(step_result, dict):
                    if "error" in step_result:
                        lines.append(f"    ✗ Error: {step_result['error']}")
                    else:
                        # Truncate long results
                        result_str = str(step_result)
                        if len(result_str) > 200:
                            result_str = result_str[:200] + "..."
                        lines.append(f"    {result_str}")
                else:
                    lines.append(f"    {step_result}")
            
            return "\n".join(lines)
        except Exception as e:
            return f"Workflow execution failed: {e}"


class MultiAgentListWorkflowsSkill(BaseSkill):
    """List available multi-agent workflows."""
    
    @property
    def name(self) -> str:
        return "multiagent.list_workflows"
    
    @property
    def description(self) -> str:
        return "List all available multi-agent workflows"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return []
    
    @property
    def category(self) -> str:
        return "multiagent"
    
    @property
    def examples(self) -> List[str]:
        return [
            "List multiagent workflows",
            "Show available workflows",
        ]
    
    def execute(self) -> str:
        orchestrator = get_orchestrator()
        workflows = orchestrator.list_workflows()
        
        if not workflows:
            return "No workflows registered"
        
        lines = ["Available Multi-Agent Workflows:"]
        descriptions = {
            "research_plan_execute_verify": "Full cycle: research → plan → execute → verify",
            "plan_execute_verify": "Plan → execute → verify (no research)",
            "parallel_research": "Parallel research from multiple angles",
            "debate": "Debate a topic with pro/con arguments",
        }
        
        for wf in workflows:
            desc = descriptions.get(wf, "Custom workflow")
            lines.append(f"  {wf}: {desc}")
        
        return "\n".join(lines)


class MultiAgentTeamStatusSkill(BaseSkill):
    """Get status of the multi-agent team."""
    
    @property
    def name(self) -> str:
        return "multiagent.team_status"
    
    @property
    def description(self) -> str:
        return "Get status of all agents in the multi-agent team"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return []
    
    @property
    def category(self) -> str:
        return "multiagent"
    
    @property
    def examples(self) -> List[str]:
        return [
            "Multiagent team status",
            "Show agent team status",
        ]
    
    def execute(self) -> str:
        orchestrator = get_orchestrator()
        status = orchestrator.get_team_status()
        
        if not status:
            return "No agents in team"
        
        lines = ["Multi-Agent Team Status:"]
        for role, info in status.items():
            lines.append(f"  {role}: {info['name']} (ID: {info['agent_id'][:8]}...)")
            lines.append(f"    Status: {info['status']}")
            if info['current_task']:
                lines.append(f"    Current Task: {info['current_task']}")
        
        return "\n".join(lines)


class MultiAgentDelegateSkill(BaseSkill):
    """Delegate a task to a specific agent."""
    
    @property
    def name(self) -> str:
        return "multiagent.delegate"
    
    @property
    def description(self) -> str:
        return "Delegate a task to a specific agent role (researcher, planner, executor, verifier, critic, summarizer)"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="task",
                type="string",
                description="Task to delegate",
                required=True,
            ),
            SkillParameter(
                name="role",
                type="string",
                description="Agent role (researcher, planner, executor, verifier, critic, summarizer)",
                required=True,
            ),
            SkillParameter(
                name="context",
                type="object",
                description="Additional context",
                required=False,
                default={},
            ),
        ]
    
    @property
    def category(self) -> str:
        return "multiagent"
    
    @property
    def examples(self) -> List[str]:
        return [
            "Delegate to researcher: find latest Python 3.12 features",
            "Delegate to planner: create plan for setting up a new project",
            "Delegate to executor: open notepad and type hello world",
            "Delegate to verifier: check if the file was created",
            "Delegate to critic: review this plan for issues",
            "Delegate to summarizer: summarize the research results",
        ]
    
    def execute(self, task: str, role: str, context: Dict = None) -> str:
        try:
            from core.multiagent.base import AgentRole
            
            orchestrator = get_orchestrator()
            
            # Map role string to enum
            role_map = {
                "researcher": AgentRole.RESEARCHER,
                "planner": AgentRole.PLANNER,
                "executor": AgentRole.EXECUTOR,
                "verifier": AgentRole.VERIFIER,
                "critic": AgentRole.CRITIC,
                "summarizer": AgentRole.SUMMARIZER,
                "coordinator": AgentRole.COORDINATOR,
            }
            
            agent_role = role_map.get(role.lower())
            if not agent_role:
                return f"Unknown role: {role}. Available: {', '.join(role_map.keys())}"
            
            result = orchestrator.coordinator._delegate(task, agent_role)
            
            if "error" in result:
                return f"✗ Delegation failed: {result['error']}"
            
            return f"✓ Delegated to {role}:\n{result}"
        except Exception as e:
            return f"Delegation failed: {e}"


class MultiAgentCustomWorkflowSkill(BaseSkill):
    """Run a custom multi-agent workflow."""
    
    @property
    def name(self) -> str:
        return "multiagent.custom_workflow"
    
    @property
    def description(self) -> str:
        return "Run a custom multi-agent workflow with defined steps"
    
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
                name="steps",
                type="array",
                description="Workflow steps: [{name, agent_role, task_template, depends_on[], timeout, required}]",
                required=True,
            ),
            SkillParameter(
                name="context",
                type="object",
                description="Additional context",
                required=False,
                default={},
            ),
        ]
    
    @property
    def category(self) -> str:
        return "multiagent"
    
    @property
    def examples(self) -> List[str]:
        return [
            'Custom workflow: goal="write a report", steps=[{"name": "research", "agent_role": "researcher", "task_template": "Research: {goal}"}, {"name": "write", "agent_role": "summarizer", "task_template": "Write report on: {goal}", "depends_on": ["research"]}]',
        ]
    
    def execute(self, goal: str, steps: List[Dict], context: Dict = None) -> str:
        try:
            orchestrator = get_orchestrator()
            result = orchestrator.run_custom_workflow(goal, steps, context or {})
            
            if "error" in result:
                return f"✗ Custom workflow failed: {result['error']}"
            
            lines = [f"✓ Custom workflow completed"]
            lines.append(f"Goal: {goal}")
            lines.append("")
            lines.append("Results:")
            
            for step_name, step_result in result.items():
                lines.append(f"  {step_name}:")
                if isinstance(step_result, dict) and "error" in step_result:
                    lines.append(f"    ✗ Error: {step_result['error']}")
                else:
                    result_str = str(step_result)
                    if len(result_str) > 200:
                        result_str = result_str[:200] + "..."
                    lines.append(f"    {result_str}")
            
            return "\n".join(lines)
        except Exception as e:
            return f"Custom workflow failed: {e}"


class MultiAgentSharedStateSkill(BaseSkill):
    """Manage shared state between agents."""
    
    @property
    def name(self) -> str:
        return "multiagent.shared_state"
    
    @property
    def description(self) -> str:
        return "Get, set, or delete shared state between agents"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="action",
                type="string",
                description="Action: get, set, delete, list",
                required=True,
            ),
            SkillParameter(
                name="key",
                type="string",
                description="State key",
                required=False,
                default="",
            ),
            SkillParameter(
                name="value",
                type="string",
                description="Value to set (for set action)",
                required=False,
                default="",
            ),
        ]
    
    @property
    def category(self) -> str:
        return "multiagent"
    
    @property
    def examples(self) -> List[str]:
        return [
            "Shared state: set key=project value=indus-phase9",
            "Shared state: get key=project",
            "Shared state: list",
            "Shared state: delete key=temp",
        ]
    
    def execute(self, action: str, key: str = "", value: str = "") -> str:
        orchestrator = get_orchestrator()
        shared_state = orchestrator.shared_state
        
        if action == "set":
            shared_state.set(key, value, "user")
            return f"Set {key} = {value}"
        elif action == "get":
            val = shared_state.get(key)
            if val is not None:
                return f"{key} = {val}"
            return f"Key '{key}' not found"
        elif action == "delete":
            if shared_state.delete(key):
                return f"Deleted {key}"
            return f"Key '{key}' not found"
        elif action == "list":
            state = shared_state.get_all()
            if not state:
                return "Shared state is empty"
            lines = ["Shared State:"]
            for k, v in state.items():
                lines.append(f"  {k} = {v}")
            return "\n".join(lines)
        else:
            return f"Unknown action: {action}. Use: get, set, delete, list"


def register_multiagent_skills(registry) -> None:
    """Register all multi-agent skills."""
    skills = [
        MultiAgentRunWorkflowSkill(),
        MultiAgentListWorkflowsSkill(),
        MultiAgentTeamStatusSkill(),
        MultiAgentDelegateSkill(),
        MultiAgentCustomWorkflowSkill(),
        MultiAgentSharedStateSkill(),
    ]
    
    for skill in skills:
        registry.register(skill.to_definition())