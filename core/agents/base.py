"""
Base Agent classes and data structures.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime
import uuid


class AgentStatus(Enum):
    """Agent execution status."""
    IDLE = "idle"
    PENDING = "pending"
    PLANNING = "planning"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AgentStep:
    """A single step in an agent plan."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    skill_name: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)
    status: AgentStatus = AgentStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "skill_name": self.skill_name,
            "parameters": self.parameters,
            "depends_on": self.depends_on,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
        }


@dataclass
class AgentPlan:
    """Complete plan for agent execution."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    goal: str = ""
    steps: List[AgentStep] = field(default_factory=list)
    status: AgentStatus = AgentStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_step(self, step: AgentStep) -> None:
        self.steps.append(step)
        self.updated_at = datetime.now()
    
    def get_step(self, step_id: str) -> Optional[AgentStep]:
        for step in self.steps:
            if step.id == step_id:
                return step
        return None
    
    def get_ready_steps(self) -> List[AgentStep]:
        """Get steps that are ready to execute (dependencies met)."""
        ready = []
        for step in self.steps:
            if step.status != AgentStatus.PENDING:
                continue
            deps_met = all(
                self.get_step(dep_id) and self.get_step(dep_id).status == AgentStatus.COMPLETED
                for dep_id in step.depends_on
            )
            if deps_met:
                ready.append(step)
        return ready
    
    def is_complete(self) -> bool:
        return all(s.status == AgentStatus.COMPLETED for s in self.steps)
    
    def has_failed(self) -> bool:
        return any(s.status == AgentStatus.FAILED for s in self.steps)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "goal": self.goal,
            "steps": [s.to_dict() for s in self.steps],
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentPlan":
        plan = cls(
            id=data.get("id", ""),
            goal=data.get("goal", ""),
            status=AgentStatus(data.get("status", "pending")),
            metadata=data.get("metadata", {}),
        )
        for step_data in data.get("steps", []):
            step = AgentStep(
                id=step_data.get("id", ""),
                name=step_data.get("name", ""),
                description=step_data.get("description", ""),
                skill_name=step_data.get("skill_name", ""),
                parameters=step_data.get("parameters", {}),
                depends_on=step_data.get("depends_on", []),
                status=AgentStatus(step_data.get("status", "pending")),
            )
            plan.add_step(step)
        return plan


@dataclass
class AgentResult:
    """Result of agent execution."""
    plan_id: str
    success: bool
    message: str = ""
    outputs: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    execution_time: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "success": self.success,
            "message": self.message,
            "outputs": self.outputs,
            "errors": self.errors,
            "execution_time": self.execution_time,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentResult":
        return cls(
            plan_id=data.get("plan_id", ""),
            success=data.get("success", False),
            message=data.get("message", ""),
            outputs=data.get("outputs", {}),
            errors=data.get("errors", []),
            execution_time=data.get("execution_time", 0.0),
        )


class Agent(ABC):
    """Abstract base class for agents."""
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.current_plan: Optional[AgentPlan] = None
    
    @abstractmethod
    def create_plan(self, goal: str, context: Dict[str, Any] = None) -> AgentPlan:
        """Create an execution plan for the given goal."""
        pass
    
    @abstractmethod
    def execute_plan(self, plan: AgentPlan) -> AgentResult:
        """Execute the plan and return result."""
        pass
    
    @abstractmethod
    def verify_result(self, plan: AgentPlan, result: AgentResult) -> AgentResult:
        """Verify the execution result and potentially adjust."""
        pass
    
    def run(self, goal: str, context: Dict[str, Any] = None) -> AgentResult:
        """Full agent workflow: plan -> execute -> verify."""
        plan = self.create_plan(goal, context)
        self.current_plan = plan
        
        result = self.execute_plan(plan)
        verified_result = self.verify_result(plan, result)
        
        return verified_result