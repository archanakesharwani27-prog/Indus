"""
LLMProvider - abstract interface for any AI backend (Gemini, OpenAI, Ollama, etc).

Har naya provider isi class ko extend karega. chat_engine.py kabhi bhi
kisi specific provider (Gemini/OpenAI) ko directly nahi jaanta - sirf
is interface ko jaanta hai. Isse naya provider add karna future mein
1 file banane jitna simple ho jaata hai.
"""

from abc import ABC, abstractmethod
from typing import List, Dict


class LLMProvider(ABC):
    """Base class jo har AI provider ko implement karna hoga."""

    @abstractmethod
    def chat(self, messages: List[Dict[str, str]]) -> str:
        """
        messages: [{"role": "user"/"assistant", "content": "..."}]
        return: AI ka text response (string)
        """
        raise NotImplementedError
