# tests/test_conversation_and_uptime_memory.py
# INDUS Test Suite: Long-Term Session Memory & Persistent Cumulative Uptime

import unittest
import time
from datetime import datetime, timedelta
from memory.db_engine import (
    db_save_conversation,
    db_get_recent_conversations,
    db_search_conversations,
    db_get_cumulative_uptime,
    db_save_cumulative_uptime,
    CURRENT_SESSION_ID,
)
from memory.memory_manager import (
    search_conversation_history,
    recall_memory,
    flush_memory_on_shutdown,
    remember,
)
from core.tool_registry import dispatch


class TestConversationAndUptimeMemory(unittest.TestCase):

    def test_session_aware_conversation_storage(self):
        """Test that conversation turns are stored with full session and date/time metadata."""
        user_msg = f"Test user message {int(time.time())}"
        indus_msg = "Test INDUS response."
        db_save_conversation(user_msg, indus_msg, intent="test_intent", summary="Unit test summary")

        recent = db_get_recent_conversations(limit=5)
        found = [c for c in recent if c.get("user_text") == user_msg]
        self.assertTrue(len(found) > 0, "Saved conversation turn was not retrieved from DB.")
        turn = found[0]
        self.assertTrue(bool(turn.get("timestamp")))
        self.assertTrue(bool(turn.get("date")))
        self.assertTrue(bool(turn.get("time_str")))
        self.assertTrue(bool(turn.get("day_name")))
        self.assertTrue(bool(turn.get("session_id")))
        self.assertEqual(turn.get("session_id"), CURRENT_SESSION_ID)

    def test_generic_history_query_returns_conversations(self):
        """Test that generic phrases like 'previous conversation' return recent history instead of empty list."""
        generic_queries = [
            "previous conversation",
            "pichli conversation",
            "past conversation",
            "last session",
            "kya baatein hui thi",
            "what did we talk about",
        ]
        for q in generic_queries:
            results = db_search_conversations(q, limit=5)
            self.assertTrue(len(results) > 0, f"Query '{q}' returned empty results when history exists.")

    def test_search_conversation_history_formatting(self):
        """Test that search_conversation_history produces clean, human-readable timeline formatting."""
        formatted = search_conversation_history("previous conversation", limit=3)
        self.assertIn("conversation turn(s) in memory", formatted)
        self.assertIn("User:", formatted)

    def test_topic_keyword_search(self):
        """Test searching past conversations by specific topic keyword."""
        unique_topic = f"quantum_superposition_{int(time.time())}"
        db_save_conversation(f"Explain {unique_topic} to me", "Here is quantum explanation.")

        results = db_search_conversations(unique_topic, limit=5)
        self.assertTrue(len(results) > 0, f"Topic search for '{unique_topic}' failed.")
        self.assertIn(unique_topic, results[0]["user_text"])

    def test_cumulative_uptime_persistence(self):
        """Test that cumulative uptime is correctly persisted and accumulated across sessions."""
        orig_uptime = db_get_cumulative_uptime()
        
        # Simulate adding 3600 seconds (1 hour)
        test_uptime = orig_uptime + 3600.0
        db_save_cumulative_uptime(test_uptime)

        loaded_uptime = db_get_cumulative_uptime()
        self.assertAlmostEqual(loaded_uptime, test_uptime, delta=1.0)

    def test_shutdown_memory_flush(self):
        """Test that flush_memory_on_shutdown executes cleanly and rapidly."""
        t0 = time.time()
        flush_memory_on_shutdown()
        elapsed_ms = (time.time() - t0) * 1000.0
        self.assertLess(elapsed_ms, 500.0, f"Memory flush took too long: {elapsed_ms:.1f}ms")

    def test_canonical_tool_registry_dispatch(self):
        """Test that search_conversation_history and recall_memory dispatch through core/tool_registry."""
        # 1. search_conversation_history
        res, err = dispatch("search_conversation_history", {"query": "previous conversation", "limit": 3})
        self.assertIsNone(err)
        self.assertIsNotNone(res)
        self.assertIn("conversation turn(s)", str(res))

        # 2. recall_memory
        remember("test_key_color", "cyan", category="preferences")
        res2, err2 = dispatch("recall_memory", {"query": "test_key_color"})
        self.assertIsNone(err2)
        self.assertIsNotNone(res2)
        self.assertIn("Cyan", str(res2).title())


if __name__ == "__main__":
    unittest.main()
