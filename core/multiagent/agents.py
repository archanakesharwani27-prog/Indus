"""
Specialized Agents - Researcher, Planner, Executor, Verifier, Coordinator.
"""

from typing import Dict, Any, List, Optional
from core.multiagent.base import (
    BaseAgent, AgentConfig, AgentRole, AgentCapability,
    AgentMessage, MessageType, AgentPlan, AgentStep, AgentStatus,
    SharedState,
)
from core.llm_provider import LLMProvider
from core.intent.registry import SkillRegistry, get_registry
from core.agents.planner import TaskPlanner
from core.agents.executor import PlanExecutor
from core.agents.verifier import ResultVerifier
from core.agents.base import AgentResult
import json


class ResearcherAgent(BaseAgent):
    """Agent specialized in gathering information and research."""
    
    def __init__(self, config: AgentConfig, registry: Optional[SkillRegistry] = None):
        if not config.capabilities:
            config.capabilities = [
                AgentCapability(
                    name="web_search",
                    description="Search the web for information",
                    skills=["web.search", "web.open_url"],
                    input_types=["query"],
                    output_types=["search_results"],
                ),
                AgentCapability(
                    name="memory_search",
                    description="Search conversation memory",
                    skills=["memory.search", "memory.recall_date"],
                    input_types=["query"],
                    output_types=["memories"],
                ),
                AgentCapability(
                    name="screen_analysis",
                    description="Analyze what's on screen",
                    skills=["vision.describe_screen", "vision.find_on_screen"],
                    input_types=["query"],
                    output_types=["screen_description"],
                ),
                AgentCapability(
                    name="fact_extraction",
                    description="Extract facts from text",
                    skills=[],
                    input_types=["text"],
                    output_types=["facts"],
                ),
            ]
        if not config.system_prompt:
            config.system_prompt = """You are a Researcher Agent. Your job is to gather information, 
search for facts, analyze data, and provide accurate information to other agents.
Be thorough, cite sources when possible, and distinguish between facts and opinions."""
        
        super().__init__(config)
        self.registry = registry or get_registry()
        self.research_history: List[Dict[str, Any]] = []
    
    def execute_task(self, task: str, context: Dict[str, Any]) -> Any:
        """Execute a research task."""
        task_lower = task.lower()
        
        # Determine research type
        if "search" in task_lower or "find" in task_lower or "look up" in task_lower:
            return self._research_web(task, context)
        elif "memory" in task_lower or "recall" in task_lower or "remember" in task_lower:
            return self._research_memory(task, context)
        elif "screen" in task_lower or "display" in task_lower:
            return self._research_screen(task, context)
        else:
            # General research using LLM
            return self._research_general(task, context)
    
    def _research_web(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Research using web search."""
        query = context.get("query", task)
        
        # Extract query from task
        import re
        query_match = re.search(r'(?:search|find|look up)\s+(?:for\s+)?(.+)', task, re.IGNORECASE)
        if query_match:
            query = query_match.group(1).strip()
        
        skill = self.registry.get_skill("web.search")
        if skill:
            if hasattr(skill, 'handler'):
                result = skill.handler(query=query)
            elif hasattr(skill, 'execute'):
                result = skill.execute(query=query)
            else:
                result = "Skill not executable"
            self.research_history.append({"type": "web", "query": query, "result": result})
            return {"source": "web", "query": query, "results": result}
        return {"error": "Web search skill not available"}
    
    def _research_memory(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Research using memory."""
        query = context.get("query", task)
        
        skill = self.registry.get_skill("memory.search")
        if skill:
            if hasattr(skill, 'handler'):
                result = skill.handler(query=query)
            elif hasattr(skill, 'execute'):
                result = skill.execute(query=query)
            else:
                result = "Skill not executable"
            self.research_history.append({"type": "memory", "query": query, "result": result})
            return {"source": "memory", "query": query, "results": result}
        return {"error": "Memory search skill not available"}
    
    def _research_screen(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Research using screen analysis."""
        skill = self.registry.get_skill("vision.describe_screen")
        if skill:
            if hasattr(skill, 'handler'):
                result = skill.handler()
            elif hasattr(skill, 'execute'):
                result = skill.execute()
            else:
                result = "Skill not executable"
            self.research_history.append({"type": "screen", "result": result})
            return {"source": "screen", "description": result}
        return {"error": "Screen analysis skill not available"}
    
    def _research_general(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """General research using LLM."""
        if self.llm:
            prompt = f"""Research this topic and provide a comprehensive answer:
            
Task: {task}
Context: {context}

Provide:
1. Key facts
2. Sources (if known)
3. Confidence level
4. Any uncertainties"""
            
            response = self.llm.chat([{"role": "user", "content": prompt}])
            self.research_history.append({"type": "general", "task": task, "result": response})
            return {"source": "llm", "task": task, "findings": response}
        return {"error": "No LLM available for general research"}
    
    def answer_query(self, question: str, context: Dict[str, Any]) -> Any:
        """Answer a research query."""
        return self.execute_task(f"research: {question}", context)


class PlannerAgent(BaseAgent):
    """Agent specialized in creating and refining plans."""
    
    def __init__(self, config: AgentConfig, registry: Optional[SkillRegistry] = None):
        if not config.capabilities:
            config.capabilities = [
                AgentCapability(
                    name="create_plan",
                    description="Create step-by-step execution plans",
                    skills=["agent.plan"],
                    input_types=["goal", "context"],
                    output_types=["plan"],
                ),
                AgentCapability(
                    name="refine_plan",
                    description="Refine plans based on feedback",
                    skills=[],
                    input_types=["plan", "feedback"],
                    output_types=["refined_plan"],
                ),
                AgentCapability(
                    name="decompose_task",
                    description="Break complex tasks into subtasks",
                    skills=[],
                    input_types=["task"],
                    output_types=["subtasks"],
                ),
            ]
        if not config.system_prompt:
            config.system_prompt = """You are a Planner Agent. Your job is to create detailed, 
actionable plans for achieving goals. Consider dependencies, available skills, 
and potential failure points. Output structured plans with clear steps."""
        
        super().__init__(config)
        self.registry = registry or get_registry()
        self.task_planner = TaskPlanner(llm_provider=self.llm, registry=self.registry)
        self.plans: Dict[str, AgentPlan] = {}
    
    def execute_task(self, task: str, context: Dict[str, Any]) -> Any:
        """Execute a planning task."""
        task_lower = task.lower()
        
        if "plan" in task_lower or "create" in task_lower:
            goal = context.get("goal", task)
            plan = self.propose_plan(goal, context)
            plan_id = plan.id
            self.plans[plan_id] = plan
            return {"plan_id": plan_id, "plan": plan.to_dict(), "steps": len(plan.steps)}
        elif "refine" in task_lower or "improve" in task_lower:
            plan_id = context.get("plan_id", "")
            feedback = context.get("feedback", task)
            return self._refine_plan(plan_id, feedback)
        elif "decompose" in task_lower or "break down" in task_lower:
            return self._decompose_task(task, context)
        
        return {"error": f"Unknown planning task: {task}"}
    
    def propose_plan(self, goal: str, context: Dict[str, Any]) -> AgentPlan:
        """Create a plan for the goal."""
        return self.task_planner.create_plan(goal, context)
    
    def _refine_plan(self, plan_id: str, feedback: str) -> Dict[str, Any]:
        """Refine a plan based on feedback."""
        if plan_id not in self.plans:
            return {"error": f"Plan {plan_id} not found"}
        
        plan = self.plans[plan_id]
        refined = self.task_planner.refine_plan(plan, feedback)
        self.plans[plan_id] = refined
        return {"plan_id": plan_id, "plan": refined.to_dict(), "refined": True}
    
    def _decompose_task(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Decompose a complex task into subtasks."""
        if self.llm:
            prompt = f"""Decompose this task into clear, actionable subtasks:

Task: {task}
Context: {context}

Return JSON array of subtasks with:
- name: subtask name
- description: what it does
- estimated_duration: rough time estimate
- dependencies: other subtasks it depends on"""
            
            response = self.llm.chat([{"role": "user", "content": prompt}])
            try:
                import re
                json_match = re.search(r'\[.*\]', response, re.DOTALL)
                if json_match:
                    subtasks = json.loads(json_match.group())
                    return {"subtasks": subtasks}
            except Exception:
                pass
        
        return {"subtasks": [], "error": "Could not decompose task"}


class ExecutorAgent(BaseAgent):
    """Agent specialized in executing plans and actions."""
    
    def __init__(self, config: AgentConfig, registry: Optional[SkillRegistry] = None):
        if not config.capabilities:
            config.capabilities = [
                AgentCapability(
                    name="execute_plan",
                    description="Execute a full plan",
                    skills=["agent.run"],
                    input_types=["goal", "plan"],
                    output_types=["results"],
                ),
                AgentCapability(
                    name="execute_step",
                    description="Execute a single step",
                    skills=[],
                    input_types=["step", "context"],
                    output_types=["result"],
                ),
                AgentCapability(
                    name="run_skill",
                    description="Run any available skill",
                    skills=["*"],
                    input_types=["skill_name", "parameters"],
                    output_types=["result"],
                ),
            ]
        if not config.system_prompt:
            config.system_prompt = """You are an Executor Agent. Your job is to execute plans 
and actions reliably. You have access to all system skills. Execute steps 
in order, handle errors gracefully, and report results accurately."""
        
        super().__init__(config)
        self.registry = registry or get_registry()
        self.executor = PlanExecutor(registry=self.registry)
        self.execution_history: List[Dict[str, Any]] = []
    
    def execute_task(self, task: str, context: Dict[str, Any]) -> Any:
        """Execute a task."""
        task_lower = task.lower()
        
        if "execute" in task_lower or "run" in task_lower:
            if "plan" in context:
                plan = context["plan"]
                if isinstance(plan, dict):
                    plan = AgentPlan.from_dict(plan)
                return self._execute_plan(plan)
            elif "goal" in context:
                return self._execute_goal(context["goal"], context.get("context", {}))
        elif "skill" in task_lower:
            skill_name = context.get("skill_name", "")
            params = context.get("parameters", {})
            return self._run_skill(skill_name, params)
        
        return {"error": f"Unknown execution task: {task}"}
    
    def _execute_plan(self, plan: AgentPlan) -> Dict[str, Any]:
        """Execute a full plan."""
        self.status = AgentStatus.EXECUTING
        result = self.executor.execute(plan)
        self.execution_history.append({"plan": plan.to_dict(), "result": result.to_dict()})
        self.status = AgentStatus.COMPLETED if result.success else AgentStatus.FAILED
        return result.to_dict()
    
    def _execute_goal(self, goal: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a goal directly (plan + execute)."""
        from core.agents import AgentWorkflow
        workflow = AgentWorkflow()
        result = workflow.run(goal, context)
        self.execution_history.append({"goal": goal, "result": result.to_dict()})
        return result.to_dict()
    
    def _run_skill(self, skill_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Run a specific skill."""
        skill = self.registry.get_skill(skill_name)
        if not skill:
            return {"error": f"Skill {skill_name} not found"}
        
        try:
            result = skill.execute(**params)
            return {"skill": skill_name, "result": result, "success": True}
        except Exception as e:
            return {"skill": skill_name, "error": str(e), "success": False}


class VerifierAgent(BaseAgent):
    """Agent specialized in verifying results and quality checking."""
    
    def __init__(self, config: AgentConfig, registry: Optional[SkillRegistry] = None):
        if not config.capabilities:
            config.capabilities = [
                AgentCapability(
                    name="verify_result",
                    description="Verify if a goal was achieved",
                    skills=["agent.verify"],
                    input_types=["goal", "result"],
                    output_types=["verification"],
                ),
                AgentCapability(
                    name="check_quality",
                    description="Check quality of outputs",
                    skills=[],
                    input_types=["output", "criteria"],
                    output_types=["quality_score"],
                ),
                AgentCapability(
                    name="validate_plan",
                    description="Validate a plan before execution",
                    skills=[],
                    input_types=["plan"],
                    output_types=["validation"],
                ),
            ]
        if not config.system_prompt:
            config.system_prompt = """You are a Verifier Agent. Your job is to verify that 
goals have been achieved, check quality of outputs, and validate plans. 
Be critical but fair. Provide specific feedback on what succeeded and what didn't."""
        
        super().__init__(config)
        self.registry = registry or get_registry()
        self.verifier = ResultVerifier(llm_provider=self.llm, registry=self.registry)
        self.verification_history: List[Dict[str, Any]] = []
    
    def execute_task(self, task: str, context: Dict[str, Any]) -> Any:
        """Execute a verification task."""
        task_lower = task.lower()
        
        if "verify" in task_lower or "check" in task_lower:
            goal = context.get("goal", "")
            result = context.get("result", {})
            if isinstance(result, dict):
                result = AgentResult.from_dict(result)
            return self._verify(goal, result)
        elif "validate" in task_lower:
            plan = context.get("plan")
            if isinstance(plan, dict):
                plan = AgentPlan.from_dict(plan)
            return self._validate_plan(plan)
        elif "quality" in task_lower:
            output = context.get("output", "")
            criteria = context.get("criteria", "")
            return self._check_quality(output, criteria)
        
        return {"error": f"Unknown verification task: {task}"}
    
    def _verify(self, goal: str, result: AgentResult) -> Dict[str, Any]:
        """Verify if goal was achieved."""
        # Create a minimal plan for verification
        plan = AgentPlan(goal=goal)
        verified = self.verifier.verify(plan, result)
        self.verification_history.append({"goal": goal, "result": verified.to_dict()})
        return verified.to_dict()
    
    def _validate_plan(self, plan: AgentPlan) -> Dict[str, Any]:
        """Validate a plan before execution."""
        issues = []
        warnings = []
        
        # Check for circular dependencies
        step_ids = {s.id for s in plan.steps}
        for step in plan.steps:
            for dep in step.depends_on:
                if dep not in step_ids:
                    issues.append(f"Step {step.id} depends on non-existent step {dep}")
        
        # Check for missing skills
        for step in plan.steps:
            if not self.registry.get_skill(step.skill_name):
                warnings.append(f"Skill {step.skill_name} not found in registry")
        
        # Check for empty steps
        if not plan.steps:
            issues.append("Plan has no steps")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "step_count": len(plan.steps),
        }
    
    def _check_quality(self, output: str, criteria: str) -> Dict[str, Any]:
        """Check quality of an output against criteria."""
        if self.llm:
            prompt = f"""Evaluate the quality of this output against the criteria:

Output: {output}
Criteria: {criteria}

Return JSON:
{{
  "score": 0-100,
  "passes": true/false,
  "strengths": [...],
  "weaknesses": [...],
  "suggestions": [...]
}}"""
            response = self.llm.chat([{"role": "user", "content": prompt}])
            try:
                import re
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
            except Exception:
                pass
        
        return {"score": 0, "passes": False, "error": "Could not evaluate quality"}


class CoordinatorAgent(BaseAgent):
    """Agent that orchestrates other agents."""
    
    def __init__(self, config: AgentConfig, message_bus, shared_state: SharedState):
        if not config.capabilities:
            config.capabilities = [
                AgentCapability(
                    name="orchestrate",
                    description="Orchestrate multiple agents to achieve a goal",
                    skills=[],
                    input_types=["goal", "agent_team"],
                    output_types=["result"],
                ),
                AgentCapability(
                    name="delegate",
                    description="Delegate tasks to specific agents",
                    skills=[],
                    input_types=["task", "agent_role"],
                    output_types=["result"],
                ),
                AgentCapability(
                    name="monitor",
                    description="Monitor agent progress and health",
                    skills=[],
                    input_types=[],
                    output_types=["status"],
                ),
            ]
        if not config.system_prompt:
            config.system_prompt = """You are a Coordinator Agent. Your job is to orchestrate 
multiple specialized agents to achieve complex goals. Delegate tasks appropriately, 
monitor progress, handle failures, and synthesize results."""
        
        super().__init__(config)
        self.message_bus = message_bus
        self.shared_state = shared_state
        self.team: Dict[AgentRole, BaseAgent] = {}
        self.active_workflows: Dict[str, Dict[str, Any]] = {}
    
    def register_team_member(self, agent: BaseAgent) -> None:
        """Register an agent as part of the team."""
        self.team[agent.role] = agent
        self.message_bus.register_agent(agent)
    
    def execute_task(self, task: str, context: Dict[str, Any]) -> Any:
        """Execute a coordination task."""
        task_lower = task.lower()
        
        if "orchestrate" in task_lower or "coordinate" in task_lower:
            goal = context.get("goal", task)
            return self._orchestrate(goal, context)
        elif "delegate" in task_lower:
            subtask = context.get("task", task)
            role = context.get("role", AgentRole.EXECUTOR)
            return self._delegate(subtask, role)
        elif "monitor" in task_lower or "status" in task_lower:
            return self._get_team_status()
        
        return {"error": f"Unknown coordination task: {task}"}
    
    def _orchestrate(self, goal: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Orchestrate multiple agents to achieve a goal."""
        workflow_id = str(uuid.uuid4())
        
        # Default workflow: Research -> Plan -> Execute -> Verify
        steps = [
            ("research", AgentRole.RESEARCHER, f"Research: {goal}"),
            ("plan", AgentRole.PLANNER, f"Create plan for: {goal}"),
            ("execute", AgentRole.EXECUTOR, f"Execute plan for: {goal}"),
            ("verify", AgentRole.VERIFIER, f"Verify result for: {goal}"),
        ]
        
        results = {}
        plan = None
        
        for step_name, role, task in steps:
            agent = self.team.get(role)
            if not agent:
                results[step_name] = {"error": f"No {role.value} agent available"}
                continue
            
            # Prepare context with previous results
            step_context = context.copy()
            step_context.update(results)
            
            if step_name == "plan" and "research" in results:
                step_context["research_findings"] = results["research"]
            elif step_name == "execute" and "plan" in results:
                step_context["plan"] = results["plan"].get("plan")
            elif step_name == "verify" and "execute" in results:
                step_context["result"] = results["execute"]
                step_context["goal"] = goal
            
            # Delegate to agent
            response = self.message_bus.request_response(
                sender_id=self.agent_id,
                sender_role=self.role,
                recipient_id=agent.agent_id,
                message_type=MessageType.TASK_REQUEST,
                content={"task": task, "context": step_context},
                timeout=60.0,
            )
            
            if response:
                if response.message_type == MessageType.TASK_RESPONSE:
                    results[step_name] = response.content.get("result")
                elif response.message_type == MessageType.ERROR:
                    results[step_name] = {"error": response.content.get("error")}
            else:
                results[step_name] = {"error": "Timeout or no response"}
        
        self.active_workflows[workflow_id] = {"goal": goal, "results": results}
        return {"workflow_id": workflow_id, "goal": goal, "results": results}
    
    def _delegate(self, task: str, role: AgentRole) -> Dict[str, Any]:
        """Delegate a task to a specific agent role."""
        agent = self.team.get(role)
        if not agent:
            return {"error": f"No {role.value} agent available"}
        
        response = self.message_bus.request_response(
            sender_id=self.agent_id,
            sender_role=self.role,
            recipient_id=agent.agent_id,
            message_type=MessageType.TASK_REQUEST,
            content={"task": task},
            timeout=30.0,
        )
        
        if response:
            if response.message_type == MessageType.TASK_RESPONSE:
                return response.content.get("result", {})
            elif response.message_type == MessageType.ERROR:
                return {"error": response.content.get("error")}
        
        return {"error": "No response from agent"}
    
    def _get_team_status(self) -> Dict[str, Any]:
        """Get status of all team members."""
        status = {}
        for role, agent in self.team.items():
            status[role.value] = {
                "agent_id": agent.agent_id,
                "name": agent.name,
                "status": agent.status.value,
                "current_task": agent.current_task,
            }
        return status


class CriticAgent(BaseAgent):
    """Agent that critiques plans and outputs."""
    
    def __init__(self, config: AgentConfig):
        if not config.capabilities:
            config.capabilities = [
                AgentCapability(
                    name="critique_plan",
                    description="Critique a plan for flaws",
                    skills=[],
                    input_types=["plan"],
                    output_types=["critique"],
                ),
                AgentCapability(
                    name="critique_output",
                    description="Critique an output for quality",
                    skills=[],
                    input_types=["output", "context"],
                    output_types=["critique"],
                ),
            ]
        if not config.system_prompt:
            config.system_prompt = """You are a Critic Agent. Your job is to find flaws, 
risks, and improvements in plans and outputs. Be constructive but thorough. 
Identify edge cases, missing steps, and potential failures."""
        
        super().__init__(config)
    
    def execute_task(self, task: str, context: Dict[str, Any]) -> Any:
        if "critique" in task.lower():
            if "plan" in context:
                return self._critique_plan(context["plan"])
            elif "output" in context:
                return self._critique_output(context["output"], context.get("context", ""))
        return {"error": "Unknown critique task"}
    
    def _critique_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        if self.llm:
            prompt = f"""Critique this plan for flaws, risks, and improvements:

Plan: {json.dumps(plan, indent=2)}

Return JSON:
{{
  "issues": [...],
  "risks": [...],
  "suggestions": [...],
  "severity": "low|medium|high"
}}"""
            response = self.llm.chat([{"role": "user", "content": prompt}])
            try:
                import re
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
            except Exception:
                pass
        return {"issues": [], "risks": [], "suggestions": [], "severity": "low"}
    
    def _critique_output(self, output: str, context: str) -> Dict[str, Any]:
        if self.llm:
            prompt = f"""Critique this output:

Output: {output}
Context: {context}

Return JSON:
{{
  "issues": [...],
  "quality_score": 0-100,
  "suggestions": [...]
}}"""
            response = self.llm.chat([{"role": "user", "content": prompt}])
            try:
                import re
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
            except Exception:
                pass
        return {"issues": [], "quality_score": 50, "suggestions": []}


class SummarizerAgent(BaseAgent):
    """Agent that summarizes outputs and conversations."""
    
    def __init__(self, config: AgentConfig):
        if not config.capabilities:
            config.capabilities = [
                AgentCapability(
                    name="summarize",
                    description="Summarize text or results",
                    skills=[],
                    input_types=["text", "max_length"],
                    output_types=["summary"],
                ),
                AgentCapability(
                    name="extract_key_points",
                    description="Extract key points from text",
                    skills=[],
                    input_types=["text"],
                    output_types=["key_points"],
                ),
            ]
        if not config.system_prompt:
            config.system_prompt = """You are a Summarizer Agent. Your job is to create 
concise, accurate summaries of text, conversations, and results. 
Focus on key information and actionable insights."""
        
        super().__init__(config)
    
    def execute_task(self, task: str, context: Dict[str, Any]) -> Any:
        text = context.get("text", "")
        max_length = context.get("max_length", 500)
        
        if "summarize" in task.lower():
            return self._summarize(text, max_length)
        elif "key points" in task.lower() or "extract" in task.lower():
            return self._extract_key_points(text)
        return {"error": "Unknown summarization task"}
    
    def _summarize(self, text: str, max_length: int) -> Dict[str, Any]:
        if self.llm and text:
            prompt = f"""Summarize this text in {max_length} characters or less:

{text}

Return JSON:
{{
  "summary": "...",
  "key_points": [...]
}}"""
            response = self.llm.chat([{"role": "user", "content": prompt}])
            try:
                import re
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
            except Exception:
                pass
        
        # Fallback: simple truncation
        return {"summary": text[:max_length], "key_points": []}
    
    def _extract_key_points(self, text: str) -> Dict[str, Any]:
        if self.llm and text:
            prompt = f"""Extract 5-10 key points from this text:

{text}

Return JSON:
{{
  "key_points": [...]
}}"""
            response = self.llm.chat([{"role": "user", "content": prompt}])
            try:
                import re
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
            except Exception:
                pass
        return {"key_points": []}


# Factory function to create agent teams
def create_default_team(
    llm_provider: Optional[LLMProvider] = None,
    registry: Optional[SkillRegistry] = None,
) -> Dict[AgentRole, BaseAgent]:
    """Create a default team of specialized agents."""
    from core.multiagent.base import AgentMessageBus, SharedState
    from core.skills.system import register_system_skills
    from core.skills.web import register_web_skills
    from core.skills.memory import register_memory_skills
    from core.skills.vision import register_vision_skills
    from core.skills.agent import register_agent_skills
    from core.skills.multiagent import register_multiagent_skills
    
    # Ensure we have a registry
    if registry is None:
        from core.intent.registry import get_registry
        registry = get_registry()
    
    # Register built-in skills
    register_system_skills(registry)
    register_web_skills(registry)
    register_memory_skills(registry)
    register_vision_skills(registry)
    register_agent_skills(registry)
    register_multiagent_skills(registry)
    
    message_bus = AgentMessageBus()
    shared_state = SharedState()
    
    agents = {}
    
    # Researcher
    researcher_config = AgentConfig(
        name="Researcher",
        role=AgentRole.RESEARCHER,
        description="Gathers information and researches topics",
        llm_provider=llm_provider,
    )
    agents[AgentRole.RESEARCHER] = ResearcherAgent(researcher_config, registry)
    
    # Planner
    planner_config = AgentConfig(
        name="Planner",
        role=AgentRole.PLANNER,
        description="Creates and refines execution plans",
        llm_provider=llm_provider,
    )
    agents[AgentRole.PLANNER] = PlannerAgent(planner_config, registry)
    
    # Executor
    executor_config = AgentConfig(
        name="Executor",
        role=AgentRole.EXECUTOR,
        description="Executes plans and actions",
        llm_provider=llm_provider,
    )
    agents[AgentRole.EXECUTOR] = ExecutorAgent(executor_config, registry)
    
    # Verifier
    verifier_config = AgentConfig(
        name="Verifier",
        role=AgentRole.VERIFIER,
        description="Verifies results and validates plans",
        llm_provider=llm_provider,
    )
    agents[AgentRole.VERIFIER] = VerifierAgent(verifier_config, registry)
    
    # Coordinator
    coordinator_config = AgentConfig(
        name="Coordinator",
        role=AgentRole.COORDINATOR,
        description="Orchestrates the agent team",
        llm_provider=llm_provider,
    )
    coordinator = CoordinatorAgent(coordinator_config, message_bus, shared_state)
    agents[AgentRole.COORDINATOR] = coordinator
    
    # Critic
    critic_config = AgentConfig(
        name="Critic",
        role=AgentRole.CRITIC,
        description="Critiques plans and outputs",
        llm_provider=llm_provider,
    )
    agents[AgentRole.CRITIC] = CriticAgent(critic_config)
    
    # Summarizer
    summarizer_config = AgentConfig(
        name="Summarizer",
        role=AgentRole.SUMMARIZER,
        description="Summarizes outputs and conversations",
        llm_provider=llm_provider,
    )
    agents[AgentRole.SUMMARIZER] = SummarizerAgent(summarizer_config)
    
    # Register all with coordinator
    for agent in agents.values():
        coordinator.register_team_member(agent)
    
    return agents