"""
IntentExecutor - Execute parsed intents with confirmation and error handling
"""

from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from core.intent.registry import SkillRegistry, get_registry
from core.persona import get_persona_prompt


@dataclass
class ExecutionResult:
    """Result of intent execution."""
    success: bool
    skill_name: str
    result: Any = None
    error: Optional[str] = None
    requires_confirmation: bool = False
    confirmation_message: Optional[str] = None


class IntentExecutor:
    """Execute parsed intents using the skill registry."""
    
    def __init__(
        self,
        registry: Optional[SkillRegistry] = None,
        confirm_callback: Optional[Callable[[str], bool]] = None,
        output_callback: Optional[Callable[[str], None]] = None,
        llm_provider: Optional[Any] = None,  # LLM provider for natural responses
        persona: str = "zoya",  # Persona for natural responses
    ):
        """
        Initialize intent executor.
        
        Args:
            registry: Skill registry (uses global if None)
            confirm_callback: Function(message) -> bool for confirmations
            output_callback: Function(message) for output messages
            llm_provider: LLM provider to generate natural responses
            persona: Persona for response generation (zoya, friendly, natural, none)
        """
        self.registry = registry or get_registry()
        self.confirm_callback = confirm_callback or self._default_confirm
        self.output_callback = output_callback or print
        self.llm_provider = llm_provider
        self.persona = persona
    
    def _default_confirm(self, message: str) -> bool:
        """Default confirmation prompt."""
        response = input(f"{message} (y/n): ").strip().lower()
        return response in ("y", "yes", "haan", "haa", "ok")
    
    def _generate_natural_response(self, skill_name: str, skill_result: Any, user_query: str = "") -> str:
        """Generate natural, persona-based response using LLM."""
        if not self.llm_provider:
            return self._format_raw_result(skill_name, skill_result)
        
        try:
            # Build prompt for LLM to generate natural response
            system_prompt = get_persona_prompt(self.persona)
            
            prompt = f"""User asked: "{user_query}"
Skill executed: {skill_name}
Skill returned: {skill_result}

Generate a warm, natural, conversational response in Zoya's style (Hinglish, friendly, caring).
Keep it concise but expressive. No bullet points, no formatting. Just natural speech.
If it's weather, make it conversational like talking to a friend.
If it's playing music, show enthusiasm and ask if they like it.
If it's an action done, confirm warmly."""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
            
            response = self.llm_provider.chat(messages)
            return response.strip()
            
        except Exception as e:
            print(f"[Executor] Natural response generation failed: {e}")
            return self._format_raw_result(skill_name, skill_result)
    
    def _format_raw_result(self, skill_name: str, skill_result: Any) -> str:
        """Fallback formatting without LLM."""
        if skill_result:
            return f"Done: {skill_result}"
        return "Done."
    
    def execute(self, intents: List[Dict[str, Any]], user_query: str = "") -> List[ExecutionResult]:
        """
        Execute a list of intents.
        
        Args:
            intents: List of intent dicts with 'name' and 'arguments'
            user_query: Original user query for natural response context
            
        Returns:
            List of ExecutionResult objects
        """
        results = []
        
        for intent in intents:
            skill_name = intent.get("name")
            arguments = intent.get("arguments", {})
            
            result = self._execute_single(skill_name, arguments)
            results.append(result)
            
            # Stop on failure if not continuing
            if not result.success and not self._should_continue_on_failure():
                break
        
        return results
    
    def _execute_single(self, skill_name: str, arguments: Dict[str, Any]) -> ExecutionResult:
        """Execute a single intent."""
        skill = self.registry.get(skill_name)
        
        if not skill:
            return ExecutionResult(
                success=False,
                skill_name=skill_name,
                error=f"Unknown skill: {skill_name}",
            )
        
        # Check confirmation requirement
        if skill.requires_confirmation:
            confirmed = self.confirm_callback(
                skill.confirmation_message or f"Execute {skill_name} with {arguments}?"
            )
            if not confirmed:
                return ExecutionResult(
                    success=False,
                    skill_name=skill_name,
                    error="User cancelled",
                    requires_confirmation=True,
                )
        
        try:
            # Execute the skill
            result = self.registry.execute(skill_name, **arguments)
            
            return ExecutionResult(
                success=True,
                skill_name=skill_name,
                result=result,
            )
            
        except Exception as e:
            return ExecutionResult(
                success=False,
                skill_name=skill_name,
                error=str(e),
            )
    
    def _should_continue_on_failure(self) -> bool:
        """Ask user if they want to continue after a failure."""
        return self.confirm_callback("Continue with next action?")
    
    def format_result(self, result: ExecutionResult, user_query: str = "") -> str:
        """Format execution result for user display with natural language."""
        if result.success:
            return self._generate_natural_response(result.skill_name, result.result, user_query)
        else:
            if result.requires_confirmation:
                return "Cancelled."
            return f"Error: {result.error}"
    
    def execute_and_format(self, intents: List[Dict[str, Any]], user_query: str = "") -> str:
        """Execute intents and return formatted response."""
        results = self.execute(intents, user_query)
        
        responses = []
        for result in results:
            formatted = self.format_result(result, user_query)
            responses.append(formatted)
            
            if self.output_callback:
                self.output_callback(formatted)
        
        return "\n".join(responses)


class StreamingIntentExecutor(IntentExecutor):
    """Executor that yields results as they complete (for streaming UI)."""
    
    def execute_stream(self, intents: List[Dict[str, Any]], user_query: str = ""):
        """Execute intents and yield results one by one."""
        for intent in intents:
            skill_name = intent.get("name")
            arguments = intent.get("arguments", {})
            
            result = self._execute_single(skill_name, arguments)
            yield result
            
            if not result.success and not self._should_continue_on_failure():
                break