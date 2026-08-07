"""
Task Planner - Creates execution plans from natural language goals.
"""

from typing import Dict, Any, List, Optional
from core.llm_provider import LLMProvider
from core.agents.base import AgentPlan, AgentStep, AgentStatus
from core.intent.registry import SkillRegistry, get_registry
import json


class TaskPlanner:
    """Creates structured plans from goals using LLM and skill registry."""
    
    def __init__(self, llm_provider: Optional[LLMProvider] = None, registry: Optional[SkillRegistry] = None):
        self.llm = llm_provider
        self.registry = registry or get_registry()
    
    def create_plan(self, goal: str, context: Dict[str, Any] = None) -> AgentPlan:
        """Create an agent plan from a goal."""
        plan = AgentPlan(goal=goal)
        
        if self.llm:
            steps = self._plan_with_llm(goal, context)
        else:
            steps = self._plan_simple(goal, context)
        
        for step_data in steps:
            step = AgentStep(
                name=step_data.get("name", ""),
                description=step_data.get("description", ""),
                skill_name=step_data.get("skill", ""),
                parameters=step_data.get("parameters", {}),
                depends_on=step_data.get("depends_on", []),
            )
            plan.add_step(step)
        
        return plan
    
    def _plan_with_llm(self, goal: str, context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Use LLM to create a detailed plan."""
        skills = self.registry.list_skills()
        skill_descriptions = "\n".join([
            f"- {s.name}: {s.description} (params: {', '.join(p.name for p in s.parameters)})"
            for s in skills
        ])
        
        context_str = ""
        if context:
            context_str = f"\nContext: {json.dumps(context, indent=2)}"
        
        prompt = f"""You are a task planner. Create a step-by-step plan to achieve the goal.

Available Skills:
{skill_descriptions}

Goal: {goal}
{context_str}

Return a JSON array of steps. Each step should have:
- name: brief step name
- description: what this step does
- skill: skill name to use (must match available skills)
- parameters: dict of parameters for the skill
- depends_on: list of step IDs this depends on (empty for first steps)

Example:
[
  {{"name": "Open browser", "description": "Open Chrome browser", "skill": "system.open_app", "parameters": {{"app_name": "chrome"}}, "depends_on": []}},
  {{"name": "Navigate to YouTube", "description": "Go to YouTube", "skill": "web.open_url", "parameters": {{"url": "https://youtube.com"}}, "depends_on": ["step_1"]}}
]

Return ONLY the JSON array:"""
        
        try:
            response = self.llm.chat([{"role": "user", "content": prompt}])
            # Extract JSON from response
            import re
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            print(f"LLM planning failed: {e}")
        
        return self._plan_simple(goal, context)
    
    def _plan_simple(self, goal: str, context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Simple heuristic-based planning for common goals."""
        goal_lower = goal.lower()
        steps = []
        
        # System app opening
        apps = {
            "notepad": "notepad",
            "calculator": "calc",
            "chrome": "chrome",
            "firefox": "firefox",
            "edge": "msedge",
            "vscode": "code",
            "code": "code",
            "terminal": "cmd",
            "cmd": "cmd",
            "powershell": "powershell",
        }
        
        for keyword, app in apps.items():
            if keyword in goal_lower:
                steps.append({
                    "name": f"Open {app}",
                    "description": f"Launch {app} application",
                    "skill": "system.open_app",
                    "parameters": {"app_name": app},
                    "depends_on": [],
                })
        
        # Web navigation
        if "youtube" in goal_lower and ("play" in goal_lower or "open" in goal_lower):
            query = goal_lower.replace("play", "").replace("youtube", "").strip()
            steps.append({
                "name": "Play YouTube",
                "description": f"Search and play on YouTube: {query}",
                "skill": "web.youtube_play",
                "parameters": {"query": query} if query else {},
                "depends_on": [],
            })
        
        if "search" in goal_lower or "google" in goal_lower:
            query = goal_lower.replace("search", "").replace("google", "").replace("for", "").strip()
            steps.append({
                "name": "Web Search",
                "description": f"Search the web for: {query}",
                "skill": "web.search",
                "parameters": {"query": query} if query else {},
                "depends_on": [],
            })
        
        # Volume control
        if "volume" in goal_lower:
            if "up" in goal_lower or "increase" in goal_lower:
                steps.append({
                    "name": "Increase Volume",
                    "description": "Increase system volume",
                    "skill": "system.volume_control",
                    "parameters": {"action": "up"},
                    "depends_on": [],
                })
            elif "down" in goal_lower or "decrease" in goal_lower:
                steps.append({
                    "name": "Decrease Volume",
                    "description": "Decrease system volume",
                    "skill": "system.volume_control",
                    "parameters": {"action": "down"},
                    "depends_on": [],
                })
            elif "mute" in goal_lower:
                steps.append({
                    "name": "Mute Volume",
                    "description": "Mute system volume",
                    "skill": "system.volume_control",
                    "parameters": {"action": "mute"},
                    "depends_on": [],
                })
            elif "set" in goal_lower:
                import re
                vol_match = re.search(r'(\d+)', goal)
                vol = int(vol_match.group(1)) if vol_match else 50
                steps.append({
                    "name": f"Set Volume to {vol}",
                    "description": f"Set system volume to {vol}%",
                    "skill": "system.volume_control",
                    "parameters": {"action": "set", "level": vol},
                    "depends_on": [],
                })
        
        # Screenshot
        if "screenshot" in goal_lower or "screen shot" in goal_lower:
            steps.append({
                "name": "Take Screenshot",
                "description": "Capture current screen",
                "skill": "system.screenshot",
                "parameters": {},
                "depends_on": [],
            })
        
        # Window management
        if "focus" in goal_lower and "window" in goal_lower:
            steps.append({
                "name": "List Windows",
                "description": "Get list of open windows",
                "skill": "system.list_windows",
                "parameters": {},
                "depends_on": [],
            })
        
        if "list" in goal_lower and "window" in goal_lower:
            steps.append({
                "name": "List Windows",
                "description": "Get list of open windows",
                "skill": "system.list_windows",
                "parameters": {},
                "depends_on": [],
            })
        
        if "show" in goal_lower and "window" in goal_lower:
            steps.append({
                "name": "List Windows",
                "description": "Get list of open windows",
                "skill": "system.list_windows",
                "parameters": {},
                "depends_on": [],
            })
        
        # Memory recall
        if "remember" in goal_lower or "recall" in goal_lower or "what did" in goal_lower:
            steps.append({
                "name": "Memory Search",
                "description": "Search conversation memory",
                "skill": "memory.search",
                "parameters": {"query": goal},
                "depends_on": [],
            })
        
        # Vision
        if "screen" in goal_lower and ("what" in goal_lower or "read" in goal_lower or "describe" in goal_lower):
            steps.append({
                "name": "Analyze Screen",
                "description": "Describe what's on screen",
                "skill": "vision.describe_screen",
                "parameters": {},
                "depends_on": [],
            })
        
        if "find" in goal_lower and "screen" in goal_lower:
            import re
            find_match = re.search(r'find\s+(.+?)\s+(?:on|in)\s+screen', goal_lower)
            target = find_match.group(1) if find_match else goal
            steps.append({
                "name": "Find on Screen",
                "description": f"Find '{target}' on screen",
                "skill": "vision.find_on_screen",
                "parameters": {"query": target},
                "depends_on": [],
            })
        
        # Default: use LLM chat if no specific skills matched
        if not steps:
            # No specific skills matched - return empty to let caller handle with direct LLM
            pass
        
        return steps
    
    def refine_plan(self, plan: AgentPlan, feedback: str) -> AgentPlan:
        """Refine a plan based on feedback."""
        if not self.llm:
            return plan
        
        prompt = f"""Refine this plan based on feedback:

Current Plan:
{plan.to_dict()}

Feedback: {feedback}

Return the refined plan as JSON array of steps (same format as before):"""
        
        try:
            response = self.llm.chat([{"role": "user", "content": prompt}])
            import re
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                new_steps = json.loads(json_match.group())
                plan.steps = []
                for step_data in new_steps:
                    step = AgentStep(
                        name=step_data.get("name", ""),
                        description=step_data.get("description", ""),
                        skill_name=step_data.get("skill", ""),
                        parameters=step_data.get("parameters", {}),
                        depends_on=step_data.get("depends_on", []),
                    )
                    plan.add_step(step)
        except Exception as e:
            print(f"Plan refinement failed: {e}")
        
        return plan