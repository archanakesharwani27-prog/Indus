"""
Phase 1 Integration Tests - Real API (NVIDIA Provider)
Tests core memory and chat engine with actual LLM calls.
Run: python -m pytest tests/test_integration_phase1.py -v
"""

import os
import sys
import pytest
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.memory import Memory
from core.chat_engine import ChatEngine
from providers.nvidia_provider import NVIDIAProvider


@pytest.fixture(scope="module")
def nvidia_provider():
    """Real NVIDIA provider for integration tests."""
    return NVIDIAProvider()


@pytest.fixture(scope="module")
def memory(tmp_path_factory):
    db_path = str(tmp_path_factory.mktemp("data") / "test_integration.db")
    return Memory(db_path=db_path)


@pytest.fixture(scope="module")
def chat_engine(memory, nvidia_provider):
    return ChatEngine(provider=nvidia_provider, memory=memory, use_intents=False, context_size=10)


class TestPhase1Integration:
    """Phase 1 integration tests with real NVIDIA API."""

    def test_memory_save_and_retrieve_real(self, memory):
        """Test memory persistence with real database."""
        memory.save_message("user", "hello integration test")
        memory.save_message("assistant", "hi there from integration")
        recent = memory.get_recent(10)
        assert len(recent) == 2
        assert recent[0]["content"] == "hello integration test"
        assert recent[1]["content"] == "hi there from integration"

    def test_chat_engine_real_llm_response(self, chat_engine):
        """Test ChatEngine gets real response from NVIDIA LLM."""
        reply = chat_engine.respond("Say exactly: INTEGRATION_TEST_PASSED")
        assert "INTEGRATION_TEST_PASSED" in reply.upper()

    def test_multi_turn_conversation(self, chat_engine, memory):
        """Test multi-turn conversation with memory persistence."""
        # Turn 1
        chat_engine.respond("My name is IntegrationTestUser")
        # Turn 2
        reply2 = chat_engine.respond("What is my name?")
        # Turn 3 - test memory context
        chat_engine.respond("Remember this number: 42")
        chat_engine.respond("Remember this color: blue")
        reply3 = chat_engine.respond("What number and color did I tell you?")
        
        # Check memory has all exchanges (4 user + 4 assistant = 8 messages)
        saved = memory.get_recent(20)
        assert len(saved) >= 8
        
        # Check LLM remembers context from turn 1
        assert "IntegrationTestUser" in reply2 or "integration" in reply2.lower()
        
        # Check LLM remembers context from turn 3
        assert "42" in reply3
        assert "blue" in reply3.lower()

    def test_chat_engine_persona_zoya(self, chat_engine):
        """Test zoya persona is applied."""
        reply = chat_engine.respond("Who are you?")
        # Should respond in character (zoya persona)
        assert len(reply) > 10  # Non-trivial response


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])