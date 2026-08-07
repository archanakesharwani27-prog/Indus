"""
GeminiProvider - real Google Gemini API se baat karta hai.
Naya `google-genai` SDK use karta hai (purana `google-generativeai` deprecated ho chuka hai).
"""

import os
from typing import List, Dict
from google import genai
from core.llm_provider import LLMProvider
from core.persona import inject_system_prompt


class GeminiProvider(LLMProvider):
    def __init__(self, model: str = "gemini-2.0-flash", persona: str = "zoya"):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY nahi mili. .env file banao aur usme "
                "GEMINI_API_KEY=your_key_here daalo."
            )
        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.persona = persona

    def chat(self, messages: List[Dict[str, str]]) -> str:
        # Inject system prompt for natural conversation
        messages = inject_system_prompt(messages, self.persona)
        
        # google-genai SDK "user"/"model" roles chahta hai, hamare
        # memory mein "assistant" hota hai isliye convert karte hain.
        contents = []
        for msg in messages:
            role = "model" if msg["role"] == "assistant" else "user"
            # System role becomes user in Gemini
            if msg["role"] == "system":
                role = "user"
            contents.append({"role": role, "parts": [{"text": msg["content"]}]})

        response = self.client.models.generate_content(
            model=self.model,
            contents=contents,
        )
        return response.text
