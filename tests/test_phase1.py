"""
Phase 1 tests - memory aur chat_engine ka core loop check karta hai.
Run: python -m pytest tests/ -v
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from core.memory import Memory
from core.chat_engine import ChatEngine
from providers.mock_provider import MockProvider


@pytest.fixture
def memory(tmp_path):
    db_path = str(tmp_path / "test.db")
    return Memory(db_path=db_path)


def test_memory_save_and_retrieve(memory):
    memory.save_message("user", "hello")
    memory.save_message("assistant", "hi there")
    recent = memory.get_recent(10)
    assert len(recent) == 2
    assert recent[0] == {"role": "user", "content": "hello"}
    assert recent[1] == {"role": "assistant", "content": "hi there"}


def test_memory_respects_order(memory):
    for i in range(5):
        memory.save_message("user", f"message {i}")
    recent = memory.get_recent(3)
    assert len(recent) == 3
    assert recent[0]["content"] == "message 2"
    assert recent[-1]["content"] == "message 4"


def test_memory_clear(memory):
    memory.save_message("user", "hello")
    memory.clear()
    assert memory.get_recent(10) == []


def test_chat_engine_basic_response(memory):
    engine = ChatEngine(provider=MockProvider(), memory=memory)
    reply = engine.respond("What is my routine?")
    assert "What is my routine?" in reply


def test_chat_engine_saves_to_memory(memory):
    engine = ChatEngine(provider=MockProvider(), memory=memory)
    engine.respond("first message")
    saved = memory.get_recent(10)
    assert len(saved) == 2  # user msg + assistant reply
    assert saved[0]["role"] == "user"
    assert saved[1]["role"] == "assistant"


def test_chat_engine_remembers_across_turns(memory):
    """Ye asli test hai jo prove karta hai memory kaam kar rahi hai -
    dusra message bhejte waqt pehle wale ka context AI ko milna chahiye."""
    engine = ChatEngine(provider=MockProvider(), memory=memory)
    engine.respond("my name is Ansh")
    reply2 = engine.respond("what did I just say?")
    # mock provider har call mein context count batata hai - agar memory
    # kaam kar rahi hai to 2nd call mein 3 messages hone chahiye
    # (1st user + 1st assistant + 2nd user)
    assert "total context messages: 3" in reply2
