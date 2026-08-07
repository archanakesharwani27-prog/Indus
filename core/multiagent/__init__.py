"""
Multi-Agent System - Multi-agent collaboration for complex tasks.
"""

from core.multiagent.base import (
    BaseAgent,
    AgentConfig,
    AgentRole,
    AgentCapability,
    AgentMessage,
    MessageType,
    AgentMessageBus,
    SharedState,
)

from core.multiagent.agents import (
    ResearcherAgent,
    PlannerAgent,
    ExecutorAgent,
    VerifierAgent,
    CoordinatorAgent,
    CriticAgent,
    SummarizerAgent,
    create_default_team,
)

from core.multiagent.orchestrator import (
    MultiAgentOrchestrator,
    MultiAgentWorkflow,
    WorkflowStep,
    WorkflowPattern,
    create_orchestrator,
)

__all__ = [
    # Base
    "BaseAgent",
    "AgentConfig",
    "AgentRole",
    "AgentCapability",
    "AgentMessage",
    "MessageType",
    "AgentMessageBus",
    "SharedState",
    # Agents
    "ResearcherAgent",
    "PlannerAgent",
    "ExecutorAgent",
    "VerifierAgent",
    "CoordinatorAgent",
    "CriticAgent",
    "SummarizerAgent",
    "create_default_team",
    # Orchestrator
    "MultiAgentOrchestrator",
    "MultiAgentWorkflow",
    "WorkflowStep",
    "WorkflowPattern",
    "create_orchestrator",
]