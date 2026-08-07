"""
MockProvider - fake AI jo bas testing ke liye hai (real API call nahi karta).
Isse hum poora system (memory, chat_engine, main loop) test kar sakte hain
bina kisi API key ya internet ke.
"""

from typing import List, Dict
from core.llm_provider import LLMProvider
from core.persona import inject_system_prompt


class MockProvider(LLMProvider):
    def __init__(self, persona: str = "zoya"):
        self.persona = persona
    
    def chat(self, messages: List[Dict[str, str]]) -> str:
        # Inject system prompt for consistency
        messages = inject_system_prompt(messages, self.persona)
        last_user_msg = messages[-1]["content"] if messages else ""
        return f"[mock reply] I heard: {last_user_msg} (total context messages: {len(messages)})"
