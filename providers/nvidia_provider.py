"""
NVIDIAProvider - NVIDIA API (Nemotron, Llama, etc.) via OpenAI-compatible endpoint
"""

import os
import re
from typing import List, Dict
from openai import OpenAI
from core.llm_provider import LLMProvider
from core.persona import inject_system_prompt


def strip_emojis(text: str) -> str:
    """Remove emojis and special Unicode characters from text."""
    # Remove emojis and other non-ASCII characters that cause issues
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags (iOS)
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "]+", flags=re.UNICODE
    )
    return emoji_pattern.sub('', text).strip()


class NVIDIAProvider(LLMProvider):
    """NVIDIA API client using OpenAI-compatible endpoint."""
    
    def __init__(
        self, 
        model: str = "nvidia/nemotron-3-ultra-550b-a55b",
        base_url: str = "https://integrate.api.nvidia.com/v1",
        persona: str = "zoya",
    ):
        api_key = os.getenv("NVIDIA_API_KEY")
        if not api_key:
            raise ValueError(
                "NVIDIA_API_KEY nahi mili. .env file mein "
                "NVIDIA_API_KEY=your_nvapi_key daalo."
            )
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
        )
        self.model = model
        self.persona = persona
    
    def chat(self, messages: List[Dict[str, str]]) -> str:
        """Send chat messages to NVIDIA API."""
        # Inject system prompt for natural conversation
        messages = inject_system_prompt(messages, self.persona)
        
        # Convert our format to OpenAI format
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
        content = response.choices[0].message.content
        return strip_emojis(content)