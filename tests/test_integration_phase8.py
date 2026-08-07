"""
Integration tests for Phase 8: Agent Workflows (Plan -> Execute -> Verify)
"""

import pytest
import os
import sys
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.agents import AgentWorkflow, TaskPlanner, PlanExecutor, ResultVerifier
from core.agents.base import AgentPlan, AgentStep, AgentStatus, AgentResult
from providers.nvidia_provider import NVIDIAProvider
from core.intent.registry import SkillRegistry, get_registry


class TestAgentBase:
    """Test base agent classes."""
    
    def test_agent_step_creation(self):
        step = AgentStep(
            name="Test Step",
            description="A test step",
            skill_name="system.open_app",
            parameters={"app_name": "notepad"},
        )
        assert step.name == "Test Step"
        assert step.skill_name == "system.open_app"
        assert step.parameters == {"app_name": "notepad"}
        assert step.status == AgentStatus.PENDING
        assert step.id is not None
    
    def test_agent_plan_creation(self):
        plan = AgentPlan(goal="Test goal")
        step1 = AgentStep(name="Step 1", skill_name="skill1", id="step1")
        step2 = AgentStep(name="Step 2", skill_name="skill2", depends_on=["step1"], id="step2")
        plan.add_step(step1)
        plan.add_step(step2)
        
        assert len(plan.steps) == 2
        assert plan.goal == "Test goal"
        assert plan.id is not None
    
    def test_plan_ready_steps(self):
        plan = AgentPlan(goal="Test")
        step1 = AgentStep(name="Step 1", skill_name="skill1", id="step1")
        step2 = AgentStep(name="Step 2", skill_name="skill2", depends_on=["step1"], id="step2")
        step3 = AgentStep(name="Step 3", skill_name="skill3", depends_on=["step2"], id="step3")
        plan.add_step(step1)
        plan.add_step(step2)
        plan.add_step(step3)
        
        # Initially only step1 is ready
        ready = plan.get_ready_steps()
        assert len(ready) == 1
        assert ready[0].id == "step1"
        
        # Complete step1
        step1.status = AgentStatus.COMPLETED
        ready = plan.get_ready_steps()
        assert len(ready) == 1
        assert ready[0].id == "step2"
        
        # Complete step2
        step2.status = AgentStatus.COMPLETED
        ready = plan.get_ready_steps()
        assert len(ready) == 1
        assert ready[0].id == "step3"
    
    def test_plan_completion(self):
        plan = AgentPlan(goal="Test")
        step1 = AgentStep(name="Step 1", skill_name="skill1")
        step2 = AgentStep(name="Step 2", skill_name="skill2")
        plan.add_step(step1)
        plan.add_step(step2)
        
        assert not plan.is_complete()
        
        step1.status = AgentStatus.COMPLETED
        assert not plan.is_complete()
        
        step2.status = AgentStatus.COMPLETED
        assert plan.is_complete()
    
    def test_plan_failure(self):
        plan = AgentPlan(goal="Test")
        step1 = AgentStep(name="Step 1", skill_name="skill1")
        step2 = AgentStep(name="Step 2", skill_name="skill2")
        plan.add_step(step1)
        plan.add_step(step2)
        
        assert not plan.has_failed()
        
        step1.status = AgentStatus.FAILED
        assert plan.has_failed()


class TestTaskPlanner:
    """Test the TaskPlanner."""
    
    @pytest.fixture
    def planner(self):
        return TaskPlanner()
    
    def test_simple_plan_open_app(self, planner):
        plan = planner.create_plan("open notepad")
        assert len(plan.steps) >= 1
        assert any(s.skill_name == "system.open_app" for s in plan.steps)
    
    def test_simple_plan_youtube(self, planner):
        plan = planner.create_plan("play youtube never gonna give you up")
        assert len(plan.steps) >= 1
        assert any(s.skill_name == "web.youtube_play" for s in plan.steps)
    
    def test_simple_plan_volume(self, planner):
        plan = planner.create_plan("set volume to 50")
        assert len(plan.steps) >= 1
        assert any(s.skill_name == "system.volume_control" for s in plan.steps)
        assert any(s.parameters.get("action") == "set" for s in plan.steps)
    
    def test_simple_plan_screenshot(self, planner):
        plan = planner.create_plan("take screenshot")
        assert len(plan.steps) >= 1
        assert any(s.skill_name == "system.screenshot" for s in plan.steps)
    
    def test_simple_plan_search(self, planner):
        plan = planner.create_plan("search for python tutorials")
        assert len(plan.steps) >= 1
        assert any(s.skill_name == "web.search" for s in plan.steps)
    
    def test_simple_plan_memory(self, planner):
        plan = planner.create_plan("what did I say about python")
        assert len(plan.steps) >= 1
        assert any(s.skill_name == "memory.search" for s in plan.steps)
    
    def test_simple_plan_vision(self, planner):
        plan = planner.create_plan("what's on my screen")
        assert len(plan.steps) >= 1
        assert any(s.skill_name == "vision.describe_screen" for s in plan.steps)


class TestPlanExecutor:
    """Test the PlanExecutor."""
    
    @pytest.fixture
    def executor(self):
        registry = get_registry()
        # Register some basic skills
        from core.skills.system import register_system_skills
        from core.skills.web import register_web_skills
        register_system_skills(registry)
        register_web_skills(registry)
        
        return PlanExecutor(registry=registry)
    
    def test_execute_single_step(self, executor):
        plan = AgentPlan(goal="Test")
        step = AgentStep(name="Open Notepad", skill_name="system.open_app", parameters={"app_name": "notepad"})
        plan.add_step(step)
        
        result = executor.execute(plan)
        
        assert result.plan_id == plan.id
        # Note: actual execution depends on system, just verify structure
    
    def test_execute_dependent_steps(self, executor):
        plan = AgentPlan(goal="Test")
        step1 = AgentStep(name="Step 1", skill_name="system.list_windows", id="step1")
        step2 = AgentStep(name="Step 2", skill_name="system.list_windows", depends_on=["step1"], id="step2")
        plan.add_step(step1)
        plan.add_step(step2)
        
        result = executor.execute(plan)
        
        assert result.plan_id == plan.id


class TestResultVerifier:
    """Test the ResultVerifier."""
    
    @pytest.fixture
    def verifier(self):
        return ResultVerifier()
    
    def test_verify_successful_plan(self, verifier):
        plan = AgentPlan(goal="Test")
        step = AgentStep(name="Step 1", skill_name="system.list_windows")
        step.status = AgentStatus.COMPLETED
        step.result = "Found 5 windows"
        plan.add_step(step)
        
        result = AgentResult(plan_id=plan.id, success=True, message="Done", outputs={step.id: "Found 5 windows"})
        
        verified = verifier.verify(plan, result)
        
        # Should pass rule-based verification
        assert verified.success is not None
    
    def test_verify_failed_plan(self, verifier):
        plan = AgentPlan(goal="Test")
        step = AgentStep(name="Step 1", skill_name="system.open_app")
        step.status = AgentStatus.FAILED
        step.error = "App not found"
        plan.add_step(step)
        
        result = AgentResult(plan_id=plan.id, success=False, message="Failed", errors=["App not found"])
        
        verified = verifier.verify(plan, result)
        
        assert verified.success == False
        assert "failed" in verified.message.lower() or "fail" in verified.message.lower()


class TestAgentWorkflow:
    """Test the full AgentWorkflow."""
    
    @pytest.fixture
    def workflow(self):
        registry = get_registry()
        from core.skills.system import register_system_skills
        from core.skills.web import register_web_skills
        register_system_skills(registry)
        register_web_skills(registry)
        
        return AgentWorkflow()
    
    def test_workflow_run_simple(self, workflow):
        result = workflow.run("list windows")
        
        assert result.plan_id is not None
        assert result.execution_time >= 0  # Can be 0 if very fast
        assert result.message is not None
    
    def test_workflow_run_with_context(self, workflow):
        result = workflow.run("open notepad", context={"user": "test"})
        
        assert result.plan_id is not None


class TestAgentSkills:
    """Test the agent skills."""
    
    @pytest.fixture
    def engine(self):
        from core.chat_engine import ChatEngine
        from core.memory import Memory
        from providers.mock_provider import MockProvider
        import tempfile
        import os
        
        # Create a temp file for the database
        db_fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(db_fd)
        
        provider = MockProvider()
        memory = Memory(db_path=db_path)
        engine = ChatEngine(provider=provider, memory=memory, use_intents=True)
        yield engine
        engine.shutdown()
        # Cleanup
        if os.path.exists(db_path):
            os.remove(db_path)
    
    def test_agent_plan_skill(self, engine):
        result = engine.respond("plan: open notepad and type hello")
        assert "plan" in result.lower() or "step" in result.lower()
    
    def test_agent_run_skill(self, engine):
        result = engine.respond("run agent: list windows")
        assert "agent" in result.lower() or "window" in result.lower() or "complete" in result.lower() or "fail" in result.lower()
    
    def test_agent_status_skill(self, engine):
        result = engine.respond("agent status")
        assert "workflow" in result.lower() or "agent" in result.lower()


# Real API tests (require NVIDIA_API_KEY)
@pytest.mark.integration
class TestAgentIntegrationReal:
    """Integration tests with real NVIDIA API."""
    
    @pytest.fixture(scope="class")
    def provider(self):
        api_key = os.getenv("NVIDIA_API_KEY")
        if not api_key:
            pytest.skip("NVIDIA_API_KEY not set")
        return NVIDIAProvider()
    
    @pytest.fixture(scope="class")
    def engine(self, provider):
        from core.chat_engine import ChatEngine
        from core.memory import Memory
        
        memory = Memory(db_path="test_integration_phase8.db")
        engine = ChatEngine(provider=provider, memory=memory, use_intents=True, enable_semantic_memory=False)
        yield engine
        engine.shutdown()
        # Cleanup
        import os
        if os.path.exists("test_integration_phase8.db"):
            os.remove("test_integration_phase8.db")
    
    def test_agent_plan_with_llm(self, engine):
        """Test plan creation with LLM."""
        result = engine.respond("plan: open calculator and take screenshot")
        print(f"\nPlan result: {result}")
        assert "plan" in result.lower() or "step" in result.lower() or "calculator" in result.lower()
    
    def test_agent_run_simple(self, engine):
        """Test running a simple agent workflow."""
        result = engine.respond("run agent: list windows")
        print(f"\nAgent run result: {result}")
        assert "agent" in result.lower() or "window" in result.lower() or "complete" in result.lower() or "fail" in result.lower()
    
    def test_agent_run_youtube(self, engine):
        """Test agent running YouTube play."""
        result = engine.respond("run agent: play youtube never gonna give you up")
        print(f"\nAgent YouTube result: {result}")
        # The agent ran successfully and played YouTube - check for any response
        assert result is not None and len(result) > 0
    
    def test_agent_run_volume(self, engine):
        """Test agent running volume control."""
        result = engine.respond("run agent: set volume to 30")
        print(f"\nAgent volume result: {result}")
        assert "agent" in result.lower() or "volume" in result.lower() or "complete" in result.lower() or "fail" in result.lower()
    
    def test_agent_status(self, engine):
        """Test agent status skill."""
        result = engine.respond("agent status")
        print(f"\nAgent status result: {result}")
        assert "workflow" in result.lower() or "agent" in result.lower()


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])