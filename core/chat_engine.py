"""
ChatEngine - Core loop with intent parsing and skill execution.
Supports both text and voice modes.
"""

from typing import List, Dict, Optional
from core.llm_provider import LLMProvider
from core.memory import Memory
from core.intent.parser import IntentParser
from core.intent.registry import SkillRegistry, get_registry
from core.intent.executor import IntentExecutor
from core.skills.system import register_system_skills
from core.skills.web import register_web_skills
from core.skills.communication import register_communication_skills
from core.skills.android import register_android_skills
from core.skills.memory import register_memory_skills
from core.skills.vision import register_vision_skills
from core.skills.proactive import register_proactive_skills
from core.skills.agent import register_agent_skills, set_workflow_llm
from core.skills.multiagent import register_multiagent_skills
from core.memory.semantic import get_semantic_memory
from core.memory.consolidation import get_consolidator
from core.persona import get_persona_prompt


class ChatEngine:
    def __init__(
        self,
        provider: LLMProvider,
        memory: Memory,
        context_size: int = 10,
        use_intents: bool = True,
        registry: Optional[SkillRegistry] = None,
        enable_semantic_memory: bool = False,
        persona: str = "zoya",
    ):
        self.provider = provider
        self.memory = memory
        self.context_size = context_size
        self.use_intents = use_intents
        self.enable_semantic_memory = enable_semantic_memory
        self.persona = persona
        
        # Initialize skill registry
        self.registry = registry or get_registry()
        self._register_builtin_skills()
        
        # Initialize semantic memory
        if self.enable_semantic_memory:
            self.semantic_memory = get_semantic_memory(
                embedding_provider="mock",
                llm_provider=provider,
                db_path="indus.db"
            )
            self.consolidator = get_consolidator(memory, self.semantic_memory, provider)
            self.consolidator.start()
        else:
            self.semantic_memory = None
            self.consolidator = None
        
        # Initialize intent parser and executor with LLM for natural responses
        if self.use_intents:
            self.intent_parser = IntentParser(self.provider, self.registry.get_schemas())
            self.intent_executor = IntentExecutor(
                self.registry,
                llm_provider=self.provider,
                persona=self.persona,
            )
            
            # Set LLM for agent workflow
            set_workflow_llm(self.provider)
        else:
            self.intent_parser = None
            self.intent_executor = None
    
    def _register_builtin_skills(self) -> None:
        """Register all built-in skills."""
        register_system_skills(self.registry)
        register_web_skills(self.registry)
        register_communication_skills(self.registry)
        register_android_skills(self.registry)
        register_memory_skills(self.registry)
        register_vision_skills(self.registry)
        register_proactive_skills(self.registry)
        register_agent_skills(self.registry)
        register_multiagent_skills(self.registry)
    
    def respond(self, user_input: str) -> str:
        """Process user input and return response."""
        # Get conversation history
        history = self.memory.get_recent(self.context_size)
        
        if self.use_intents and self.intent_parser:
            # Try intent-based processing
            return self._respond_with_intents(user_input, history)
        else:
            # Fallback to direct LLM chat
            return self._respond_direct(user_input, history)
    
    def _respond_with_intents(self, user_input: str, history: List[Dict[str, str]]) -> str:
        """Process using intent parsing and skill execution."""
        try:
            # Parse intent
            intents = self.intent_parser.parse(user_input, history)
            
            if not intents:
                # No intent matched - use LLM for conversational response
                response = self._respond_direct(user_input, history)
            else:
                # Execute intents with natural language formatting
                response = self.intent_executor.execute_and_format(intents, user_input)
        
        except Exception as e:
            # Fallback to direct LLM on any error
            response = self._respond_direct(user_input, history)
        
        # Save to memory
        self.memory.save_message("user", user_input)
        self.memory.save_message("assistant", response)
        
        # Also add to semantic memory for long-term recall
        if self.semantic_memory:
            try:
                self.semantic_memory.add_conversation(user_input, response)
            except Exception:
                pass  # Don't fail response if semantic memory fails
        
        return response
    
    def _respond_direct(self, user_input: str, history: List[Dict[str, str]]) -> str:
        """Direct LLM response (original behavior)."""
        messages = history + [{"role": "user", "content": user_input}]
        reply = self.provider.chat(messages)
        
        # Save to memory
        self.memory.save_message("user", user_input)
        self.memory.save_message("assistant", reply)
        
        return reply
    
    def set_voice_mode(self, enabled: bool) -> None:
        """Enable/disable voice mode (placeholder for future TTS integration)."""
        pass
    
    def get_available_skills(self) -> List[Dict]:
        """Get list of available skills for help display."""
        skills = []
        for skill in self.registry.list_skills():
            skills.append({
                "name": skill.name,
                "description": skill.description,
                "category": skill.category,
                "examples": skill.examples,
            })
        return skills
    
    def shutdown(self):
        """Clean shutdown."""
        if self.consolidator:
            self.consolidator.stop()