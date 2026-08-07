"""
Integration tests for Phase 9: Multi-Agent Collaboration.
"""

import pytest
import os
import sys
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.multiagent import (
    BaseAgent, AgentConfig, AgentRole, AgentCapability,
    AgentMessage, MessageType, AgentMessageBus, SharedState,
    ResearcherAgent, PlannerAgent, ExecutorAgent, VerifierAgent,
    CoordinatorAgent, CriticAgent, SummarizerAgent,
    MultiAgentOrchestrator, MultiAgentWorkflow, WorkflowStep, WorkflowPattern,
    create_orchestrator, create_default_team,
)
from core.intent.registry import SkillRegistry, get_registry
from providers.mock_provider import MockProvider


class TestMultiAgentBase:
    """Test base multi-agent classes."""
    
    def test_agent_config_creation(self):
        config = AgentConfig(
            name="TestAgent",
            role=AgentRole.RESEARCHER,
            description="A test agent",
        )
        assert config.name == "TestAgent"
        assert config.role == AgentRole.RESEARCHER
        assert config.agent_id is not None
    
    def test_agent_message_creation(self):
        msg = AgentMessage(
            sender_id="agent1",
            sender_role=AgentRole.RESEARCHER,
            recipient_id="agent2",
            message_type=MessageType.TASK_REQUEST,
            content={"task": "research python"},
        )
        assert msg.sender_id == "agent1"
        assert msg.message_type == MessageType.TASK_REQUEST
        assert msg.content["task"] == "research python"
        assert msg.requires_response is False
    
    def test_message_bus_register(self):
        bus = AgentMessageBus()
        config = AgentConfig(name="Test", role=AgentRole.RESEARCHER)
        agent = BaseAgent(config)
        bus.register_agent(agent)
        
        assert agent.agent_id in bus.agents
    
    def test_shared_state(self):
        state = SharedState()
        state.set("key1", "value1", "agent1")
        assert state.get("key1") == "value1"
        
        state.set("key1", "value2", "agent2")
        assert state.get("key1") == "value2"
        
        all_state = state.get_all()
        assert all_state["key1"] == "value2"
        
        state.delete("key1")
        assert state.get("key1") is None


class TestSpecializedAgents:
    """Test specialized agent implementations."""
    
    @pytest.fixture
    def registry(self):
        return get_registry()
    
    @pytest.fixture
    def mock_llm(self):
        return MockProvider()
    
    def test_researcher_agent_creation(self, registry, mock_llm):
        config = AgentConfig(
            name="Researcher",
            role=AgentRole.RESEARCHER,
            llm_provider=mock_llm,
        )
        agent = ResearcherAgent(config, registry)
        assert agent.role == AgentRole.RESEARCHER
        assert len(agent.capabilities) > 0
    
    def test_planner_agent_creation(self, registry, mock_llm):
        config = AgentConfig(
            name="Planner",
            role=AgentRole.PLANNER,
            llm_provider=mock_llm,
        )
        agent = PlannerAgent(config, registry)
        assert agent.role == AgentRole.PLANNER
        assert agent.task_planner is not None
    
    def test_executor_agent_creation(self, registry, mock_llm):
        config = AgentConfig(
            name="Executor",
            role=AgentRole.EXECUTOR,
            llm_provider=mock_llm,
        )
        agent = ExecutorAgent(config, registry)
        assert agent.role == AgentRole.EXECUTOR
        assert agent.executor is not None
    
    def test_verifier_agent_creation(self, registry, mock_llm):
        config = AgentConfig(
            name="Verifier",
            role=AgentRole.VERIFIER,
            llm_provider=mock_llm,
        )
        agent = VerifierAgent(config, registry)
        assert agent.role == AgentRole.VERIFIER
        assert agent.verifier is not None
    
    def test_coordinator_agent_creation(self, mock_llm):
        bus = AgentMessageBus()
        state = SharedState()
        config = AgentConfig(
            name="Coordinator",
            role=AgentRole.COORDINATOR,
            llm_provider=mock_llm,
        )
        agent = CoordinatorAgent(config, bus, state)
        assert agent.role == AgentRole.COORDINATOR
    
    def test_critic_agent_creation(self, mock_llm):
        config = AgentConfig(
            name="Critic",
            role=AgentRole.CRITIC,
            llm_provider=mock_llm,
        )
        agent = CriticAgent(config)
        assert agent.role == AgentRole.CRITIC
    
    def test_summarizer_agent_creation(self, mock_llm):
        config = AgentConfig(
            name="Summarizer",
            role=AgentRole.SUMMARIZER,
            llm_provider=mock_llm,
        )
        agent = SummarizerAgent(config)
        assert agent.role == AgentRole.SUMMARIZER


class TestAgentCommunication:
    """Test inter-agent communication."""
    
    @pytest.fixture
    def bus(self):
        return AgentMessageBus()
    
    @pytest.fixture
    def researcher(self, bus):
        config = AgentConfig(name="Researcher", role=AgentRole.RESEARCHER)
        agent = ResearcherAgent(config)
        bus.register_agent(agent)
        return agent
    
    @pytest.fixture
    def planner(self, bus):
        config = AgentConfig(name="Planner", role=AgentRole.PLANNER)
        agent = PlannerAgent(config)
        bus.register_agent(agent)
        return agent
    
    def test_direct_message(self, bus, researcher, planner):
        """Test direct message between agents."""
        msg = AgentMessage(
            sender_id=researcher.agent_id,
            sender_role=AgentRole.RESEARCHER,
            recipient_id=planner.agent_id,
            message_type=MessageType.INFO_SHARE,
            content={"info": "test data"},
        )
        
        bus.send_message(msg)
        
        # Check planner received it
        assert len(planner._inbox) == 1
        assert planner._inbox[0].content["info"] == "test data"
    
    def test_broadcast_message(self, bus, researcher, planner):
        """Test broadcast message."""
        bus.broadcast(
            sender_id=researcher.agent_id,
            sender_role=AgentRole.RESEARCHER,
            message_type=MessageType.INFO_SHARE,
            content={"broadcast": "hello all"},
        )
        
        # Both should receive (but sender might not)
        assert len(planner._inbox) >= 1
    
    def test_request_response(self, bus, researcher, planner):
        """Test request-response pattern."""
        # This is a simplified test - actual request_response is more complex
        msg = AgentMessage(
            sender_id=researcher.agent_id,
            sender_role=AgentRole.RESEARCHER,
            recipient_id=planner.agent_id,
            message_type=MessageType.QUERY,
            content={"question": "What is 2+2?"},
            requires_response=True,
        )
        
        bus.send_message(msg)
        
        assert len(planner._inbox) == 1
        assert planner._inbox[0].message_type == MessageType.QUERY


class TestMultiAgentOrchestrator:
    """Test the multi-agent orchestrator."""
    
    @pytest.fixture
    def orchestrator(self):
        return create_orchestrator(llm_provider=MockProvider())
    
    def test_orchestrator_creation(self, orchestrator):
        assert orchestrator is not None
        assert len(orchestrator.team) > 0
        assert AgentRole.COORDINATOR in orchestrator.team
        assert AgentRole.RESEARCHER in orchestrator.team
        assert AgentRole.PLANNER in orchestrator.team
        assert AgentRole.EXECUTOR in orchestrator.team
        assert AgentRole.VERIFIER in orchestrator.team
        assert AgentRole.CRITIC in orchestrator.team
        assert AgentRole.SUMMARIZER in orchestrator.team
    
    def test_list_workflows(self, orchestrator):
        workflows = orchestrator.list_workflows()
        assert "research_plan_execute_verify" in workflows
        assert "plan_execute_verify" in workflows
        assert "parallel_research" in workflows
        assert "debate" in workflows
    
    def test_get_workflow(self, orchestrator):
        wf = orchestrator.get_workflow("research_plan_execute_verify")
        assert wf is not None
        assert wf.name == "research_plan_execute_verify"
        assert len(wf.steps) == 4
    
    def test_team_status(self, orchestrator):
        status = orchestrator.get_team_status()
        assert len(status) == 7  # 7 default agents
        for role, info in status.items():
            assert "agent_id" in info
            assert "name" in info
            assert "status" in info
    
    def test_shared_state_access(self, orchestrator):
        orchestrator.shared_state.set("test_key", "test_value", "test_agent")
        assert orchestrator.shared_state.get("test_key") == "test_value"


class TestWorkflows:
    """Test workflow execution (with mock provider)."""
    
    @pytest.fixture
    def orchestrator(self):
        return create_orchestrator(llm_provider=MockProvider())
    
    def test_plan_execute_verify_workflow(self, orchestrator):
        """Test the plan_execute_verify workflow."""
        # This tests the workflow structure, not actual execution
        # since we're using mock provider
        result = orchestrator.run_workflow("plan_execute_verify", "open notepad")
        
        assert "workflow_id" in result
        assert result["goal"] == "open notepad"
        assert "results" in result
        # With mock provider, steps should complete (even if with mock results)
        assert len(result["results"]) > 0
    
    def test_research_plan_execute_verify_workflow(self, orchestrator):
        """Test the full research workflow."""
        result = orchestrator.run_workflow("research_plan_execute_verify", "open notepad")
        
        assert "workflow_id" in result
        assert "results" in result
        # Should have 4 steps: research, plan, execute, verify
        assert len(result["results"]) >= 3  # At least some steps
    
    def test_parallel_research_workflow(self, orchestrator):
        """Test parallel research workflow."""
        result = orchestrator.run_workflow("parallel_research", "test topic")
        
        assert "workflow_id" in result
        assert "results" in result
    
    def test_debate_workflow(self, orchestrator):
        """Test debate workflow."""
        result = orchestrator.run_workflow("debate", "test topic")
        
        assert "workflow_id" in result
        assert "results" in result
    
    def test_custom_workflow(self, orchestrator):
        """Test custom workflow."""
        steps = [
            {
                "name": "step1",
                "agent_role": "researcher",
                "task_template": "Research: {goal}",
            },
            {
                "name": "step2",
                "agent_role": "summarizer",
                "task_template": "Summarize: {goal}",
                "depends_on": ["step1"],
            },
        ]
        
        result = orchestrator.run_custom_workflow("open notepad", steps)
        
        # run_custom_workflow returns step results directly
        assert "step1" in result
        assert "step2" in result


class TestMultiAgentSkills:
    """Test multi-agent skills via ChatEngine."""
    
    @pytest.fixture
    def engine(self):
        from core.chat_engine import ChatEngine
        from core.memory import Memory
        import tempfile
        import os
        
        db_fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(db_fd)
        
        provider = MockProvider()
        memory = Memory(db_path=db_path)
        engine = ChatEngine(provider=provider, memory=memory, use_intents=True)
        yield engine
        engine.shutdown()
        if os.path.exists(db_path):
            os.remove(db_path)
    
    def test_list_workflows_skill(self, engine):
        result = engine.respond("list multiagent workflows")
        assert "workflow" in result.lower() or "research_plan_execute_verify" in result
    
    def test_team_status_skill(self, engine):
        result = engine.respond("multiagent team status")
        assert "team" in result.lower() or "agent" in result.lower()
    
    def test_delegate_skill(self, engine):
        result = engine.respond("delegate to researcher: find python info")
        assert "researcher" in result.lower() or "delegat" in result.lower()
    
    def test_shared_state_skill(self, engine):
        result = engine.respond("shared state: set key=test value=hello")
        assert "set" in result.lower() or "test" in result.lower()
        
        result = engine.respond("shared state: get key=test")
        assert "hello" in result.lower() or "test" in result.lower()
    
    def test_run_workflow_skill(self, engine):
        # This will run a mock workflow
        result = engine.respond("run multiagent workflow plan_execute_verify: open notepad")
        assert "workflow" in result.lower() or "plan" in result.lower() or "execut" in result.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])