"""
Phase 7 Integration Tests - Proactive Intelligence & Plugin System
Tests proactive monitoring, routine learning, suggestions, and plugin loading.
Run: python -m pytest tests/test_integration_phase7.py -v -s
"""

import os
import sys
import pytest
import time
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_proactive_context_monitor():
    """Test ContextMonitor captures active app, window, time."""
    from core.proactive.context import ContextMonitor, ContextSnapshot
    
    print("Testing ContextMonitor...")
    monitor = ContextMonitor(interval_seconds=2)
    
    # Start monitoring
    monitor.start()
    
    # Wait for a few snapshots
    time.sleep(5)
    
    # Get context history
    history = monitor.get_history(limit=5)
    print(f"Context history ({len(history)} entries):")
    for ctx in history:
        idle = getattr(ctx, 'user_idle_seconds', 0)
        print(f"  App: {ctx.active_app}, Window: {ctx.window_title[:50]}, Idle: {idle:.0f}s")
    
    monitor.stop()
    
    assert len(history) > 0, "No context captured"
    assert all(hasattr(ctx, 'active_app') for ctx in history)
    assert all(hasattr(ctx, 'window_title') for ctx in history)


def test_proactive_routine_learner():
    """Test RoutineLearner detects patterns."""
    from core.proactive.routines import RoutineLearner
    
    print("Testing RoutineLearner...")
    learner = RoutineLearner(db_path="test_routines.db")
    
    # Add some mock events
    import time as time_module
    from datetime import datetime
    
    # Simulate routine: open chrome at 9am
    test_events = [
        {"event_type": "app_launch", "data": {"app": "chrome"}},
        {"event_type": "app_launch", "data": {"app": "vscode"}},
        {"event_type": "app_launch", "data": {"app": "chrome"}},
        {"event_type": "app_launch", "data": {"app": "vscode"}},
    ]
    
    for event in test_events:
        learner.record_event(event["event_type"], event["data"])
    
    # Analyze routines
    routines = learner.analyze_patterns()
    print(f"Detected routines: {routines}")
    
    assert isinstance(routines, list)


def test_proactive_suggestion_engine():
    """Test SuggestionEngine generates suggestions."""
    from core.proactive.suggestions import SuggestionEngine
    from core.proactive.context import ContextSnapshot
    from datetime import datetime
    
    print("Testing SuggestionEngine...")
    engine = SuggestionEngine()
    
    # Create mock context snapshot with correct fields
    ctx = ContextSnapshot(
        timestamp=time.time(),
        active_app="Code.exe",
        window_title="Visual Studio Code",
        user_idle_seconds=0,
        time_of_day="14:30",
    )
    
    # Generate suggestions (internal method)
    suggestions = engine._generate_suggestions(ctx)
    print(f"Suggestions: {suggestions}")
    
    assert isinstance(suggestions, list)
    
    engine.stop()


def test_proactive_skills_via_chatengine():
    """Test proactive skills through ChatEngine."""
    from core.chat_engine import ChatEngine
    from core.memory import Memory
    from providers.nvidia_provider import NVIDIAProvider
    
    print("Testing proactive skills via ChatEngine...")
    memory = Memory(db_path="test_proactive.db")
    provider = NVIDIAProvider()
    engine = ChatEngine(provider=provider, memory=memory, use_intents=True, enable_semantic_memory=False)
    
    # Test start proactive
    reply = engine.respond("start proactive assistant")
    print(f"Start proactive: {reply}")
    assert "start" in reply.lower() or "proactive" in reply.lower() or "shuru" in reply.lower()
    
    time.sleep(2)
    
    # Test show suggestions
    reply = engine.respond("show suggestions")
    print(f"Show suggestions: {reply}")
    
    # Test analyze routines
    reply = engine.respond("analyze my routines")
    print(f"Analyze routines: {reply}")
    
    # Test context status
    reply = engine.respond("current context")
    print(f"Context status: {reply}")
    
    # Test routine stats
    reply = engine.respond("routine statistics")
    print(f"Routine stats: {reply}")
    
    # Stop proactive
    reply = engine.respond("stop proactive assistant")
    print(f"Stop proactive: {reply}")
    assert "stop" in reply.lower() or "band" in reply.lower() or "ruka" in reply.lower()


def test_plugin_load():
    """Test plugin loading system."""
    from core.chat_engine import ChatEngine
    from core.memory import Memory
    from providers.nvidia_provider import NVIDIAProvider
    
    print("Testing plugin loading...")
    memory = Memory(db_path="test_plugin.db")
    provider = NVIDIAProvider()
    engine = ChatEngine(provider=provider, memory=memory, use_intents=True, enable_semantic_memory=False)
    
    # Load plugins
    reply = engine.respond("load plugins")
    print(f"Load plugins: {reply}")
    
    # Should discover example_skills plugin
    assert "load" in reply.lower() or "plugin" in reply.lower() or "discover" in reply.lower()


def test_custom_plugin_skills():
    """Test custom plugin skills work."""
    from core.chat_engine import ChatEngine
    from core.memory import Memory
    from providers.nvidia_provider import NVIDIAProvider
    
    print("Testing custom plugin skills...")
    memory = Memory(db_path="test_custom_plugin.db")
    provider = NVIDIAProvider()
    engine = ChatEngine(provider=provider, memory=memory, use_intents=True, enable_semantic_memory=False)
    
    # Test calc skill
    reply = engine.respond("calc 2 + 2")
    print(f"Calc: {reply}")
    assert "4" in reply or "result" in reply.lower()
    
    # Test weather skill
    reply = engine.respond("weather in Delhi")
    print(f"Weather: {reply}")
    assert "delhi" in reply.lower() or "weather" in reply.lower()
    
    # Test timer skill
    reply = engine.respond("timer set 1m")
    print(f"Timer set: {reply}")
    
    reply = engine.respond("timer status")
    print(f"Timer status: {reply}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])