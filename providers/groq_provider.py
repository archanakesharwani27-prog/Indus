"""
GroqProvider - Groq API for ultra-fast LLM inference (Llama, Mixtral, Gemma, etc.)
"""

import os
from typing import List, Dict
from groq import Groq
from core.llm_provider import LLMProvider
from core.persona import inject_system_prompt


class GroqProvider(LLMProvider):
    """Groq API client - ultra-fast inference for Llama, Mixtral, Gemma models."""
    
    # Available models on Groq (as of 2025)
    AVAILABLE_MODELS = {
        "llama-3.3-70b-versatile": "Llama 3.3 70B (best quality)",
        "llama-3.1-8b-instant": "Llama 3.1 8B (fastest)",
        "groq/compound": "Groq Compound (reasoning)",
        "groq/compound-mini": "Groq Compound Mini (fast reasoning)",
        "qwen/qwen3.6-27b": "Qwen 3.6 27B",
        "allam-2-7b": "ALLaM 2 7B (Arabic)",
        "meta-llama/llama-prompt-guard-2-22m": "Llama Prompt Guard 22M",
        "meta-llama/llama-prompt-guard-2-86m": "Llama Prompt Guard 86M",
    }
    
    def __init__(
        self, 
        model: str = "llama-3.3-70b-versatile",
        base_url: str = None,  # Not needed for Groq
        persona: str = "zoya",
    ):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError(
                "GROQ_API_KEY nahi mili. .env file mein "
                "GROQ_API_KEY=your_groq_key daalo."
            )
        self.client = Groq(api_key=api_key)
        self.model = model
        self.persona = persona
        
        if model not in self.AVAILABLE_MODELS:
            print(f"[Groq] Warning: Model '{model}' may not be available. Available: {list(self.AVAILABLE_MODELS.keys())}")
    
    def chat(self, messages: List[Dict[str, str]]) -> str:
        """Send chat messages to Groq API."""
        # Inject system prompt for natural conversation
        messages = inject_system_prompt(messages, self.persona)
        
        # Convert our format to OpenAI format (Groq uses OpenAI-compatible API)
        openai_messages = []
        for msg in messages:
            role = "assistant" if msg["role"] == "assistant" else msg["role"]
            openai_messages.append({"role": role, "content": msg["content"]})
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=openai_messages,
            temperature=0.7,
            max_tokens=4096,
        )
        return response.choices[0].message.content
    
    @classmethod
    def list_models(cls):
        """List available models."""
        return cls.AVAILABLE_MODELS