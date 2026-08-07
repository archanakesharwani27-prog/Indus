"""
IntentParser - LLM-based intent parsing with function calling (provider-agnostic)
"""

import json
import os
from typing import List, Dict, Any, Optional
from core.llm_provider import LLMProvider


class IntentParser:
    """Parse user input into structured intents using LLM function calling."""
    
    def __init__(
        self,
        llm_provider: LLMProvider,
        skills_schema: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
    ):
        """
        Initialize intent parser.
        
        Args:
            llm_provider: LLM provider for parsing (any provider - NVIDIA, Gemini, etc.)
            skills_schema: List of skill definitions (OpenAI function format)
            system_prompt: Custom system prompt
        """
        self.llm_provider = llm_provider
        self.skills_schema = skills_schema
        self.system_prompt = system_prompt or self._default_system_prompt()
    
    def _default_system_prompt(self) -> str:
        schema_json = json.dumps(self.skills_schema, indent=2)
        return f"""You are Indus, a personal AI assistant that converts user requests into structured function calls.

Available skills (functions):
{schema_json}

Your job:
1. Understand the user's intent
2. Select the appropriate skill(s) from the list above
3. Extract required parameters from the user's request
4. Return a JSON response with function calls

Rules:
- Only call functions that are defined in the available skills above
- If the request is ambiguous, ask for clarification
- If no skill matches, respond with a helpful message explaining what you can do
- For multi-step requests, you can return multiple function calls
- Always extract parameters from the user's natural language - don't make up values
- Return ONLY valid JSON, no extra text

Language: The user may speak in Hindi, English, or Hinglish. Understand all three.

Response format (JSON only):
{{
  "function_calls": [
    {{"name": "skill.name", "arguments": {{"param": "value"}}}},
    ...
  ]
}}"""
    
    def parse(self, user_input: str, context: Optional[List[Dict[str, str]]] = None) -> List[Dict[str, Any]]:
        """
        Parse user input into intent(s).
        
        Args:
            user_input: User's natural language input
            context: Optional conversation context
            
        Returns:
            List of function calls (each with 'name' and 'arguments')
        """
        messages = [
            {"role": "system", "content": self.system_prompt},
        ]
        
        if context:
            messages.extend(context)
        
        messages.append({"role": "user", "content": user_input})
        
        try:
            # Use the existing LLM provider (NVIDIA, Gemini, etc.)
            response = self.llm_provider.chat(messages)
            
            # Parse JSON response
            parsed = json.loads(response)
            function_calls = parsed.get("function_calls", [])
            
            # Convert to standard format
            intents = []
            for call in function_calls:
                intents.append({
                    "name": call.get("name"),
                    "arguments": call.get("arguments", {}),
                })
            
            return intents
            
        except json.JSONDecodeError:
            # Fallback to keyword matching if LLM doesn't return valid JSON
            return self._fallback_parse(user_input)
        except Exception as e:
            print(f"Intent parsing error: {e}")
            return self._fallback_parse(user_input)
    
    def _fallback_parse(self, user_input: str) -> List[Dict[str, Any]]:
        """Fallback parsing using keyword matching."""
        user_lower = user_input.lower()
        intents = []
        
        # Check for phone/android context first
        is_phone_context = any(w in user_lower for w in ["phone", "android", "mobile"])
        
        # Simple keyword-based intent detection
        # Order matters: more specific keywords first
        if is_phone_context:
            skill_keywords = {
                "android.open_app": ["open on phone", "launch on phone", "open on android", "phone open", "open ", "launch ", "start "],
                "android.tap": ["tap on phone", "tap phone", "click on phone"],
                "android.swipe": ["swipe on phone", "swipe phone", "scroll on phone"],
                "android.type_text": ["type on phone", "type on android", "enter text on phone"],
                "android.get_notifications": ["phone notifications", "notifications on phone", "android notifications"],
                "android.media_control": ["play on phone", "pause on phone", "music on phone", "media on phone", "play music on phone", "play music", "play ", "pause "],
                "android.answer_call": ["answer call on phone", "pick up phone call"],
                "android.decline_call": ["decline call on phone", "reject call on phone"],
                "android.open_youtube": ["youtube on phone", "open youtube on phone", "play on youtube phone", "youtube "],
                "android.screenshot": ["screenshot phone", "phone screenshot"],
                "android.device_info": ["phone info", "android info", "device info"],
                "system.open_app": ["open ", "launch ", "start ", "run "],
                "system.run_command": ["command", "execute", "run command", "shell"],
                "web.open_url": ["open website", "go to", "visit"],
                "web.search": ["search", "google", "find"],
                "web.youtube_play": ["youtube", "play video", "watch"],
                "system.volume_control": ["volume", "sound", "mute", "unmute"],
                "system.list_windows": ["list windows", "show windows", "open windows", "all windows"],
                "system.focus_window": ["focus", "bring to front", "switch to", "activate"],
                "system.minimize_window": ["minimize", "minimise"],
                "system.maximize_window": ["maximize", "maximise"],
                "system.screenshot": ["screenshot", "capture screen", "take screenshot"],
                "system.read_screen": ["read screen", "screen text", "ocr", "describe screen", "what on screen"],
            }
        else:
            skill_keywords = {
                "system.open_app": ["open", "launch", "start", "run"],
                "system.run_command": ["command", "execute", "run command", "shell"],
                "web.open_url": ["open website", "go to", "visit"],
                "web.search": ["search", "google", "find"],
                "web.youtube_play": ["youtube", "play video", "watch"],
                "system.volume_control": ["volume", "sound", "mute", "unmute"],
                "system.list_windows": ["list windows", "show windows", "open windows", "all windows"],
                "system.focus_window": ["focus", "bring to front", "switch to", "activate"],
                "system.minimize_window": ["minimize", "minimise"],
                "system.maximize_window": ["maximize", "maximise"],
                "system.screenshot": ["screenshot", "capture screen", "take screenshot"],
                "system.read_screen": ["read screen", "screen text", "ocr", "describe screen", "what on screen"],
            }
        
        for skill_name, keywords in skill_keywords.items():
            if any(kw in user_lower for kw in keywords):
                args = self._extract_args(skill_name, user_input)
                intents.append({"name": skill_name, "arguments": args})
                break  # Only match first for fallback
        
        return intents
    
    def _extract_args(self, skill_name: str, user_input: str) -> Dict[str, Any]:
        """Extract arguments for a skill (simplified)."""
        if skill_name == "system.open_app":
            for keyword in ["open", "launch", "start", "run"]:
                if keyword in user_input.lower():
                    parts = user_input.lower().split(keyword, 1)
                    if len(parts) > 1:
                        app_name = parts[1].strip()
                        return {"app_name": app_name}
            return {"app_name": user_input}
        
        elif skill_name == "web.search":
            for keyword in ["search", "google", "find"]:
                if keyword in user_input.lower():
                    parts = user_input.lower().split(keyword, 1)
                    if len(parts) > 1:
                        return {"query": parts[1].strip()}
            return {"query": user_input}
        
        elif skill_name == "web.youtube_play":
            for keyword in ["youtube", "play video", "watch"]:
                if keyword in user_input.lower():
                    parts = user_input.lower().split(keyword, 1)
                    if len(parts) > 1:
                        return {"query": parts[1].strip()}
            return {"query": user_input}
        
        elif skill_name == "system.volume_control":
            user_lower = user_input.lower()
            if "mute" in user_lower:
                return {"action": "mute"}
            elif "unmute" in user_lower:
                return {"action": "unmute"}
            elif "up" in user_lower or "increase" in user_lower or "higher" in user_lower:
                return {"action": "up"}
            elif "down" in user_lower or "decrease" in user_lower or "lower" in user_lower:
                return {"action": "down"}
            elif "set" in user_lower or "to" in user_lower:
                import re
                numbers = re.findall(r'\d+', user_input)
                if numbers:
                    return {"action": "set", "level": int(numbers[0])}
                return {"action": "get"}
            else:
                return {"action": "get"}
        
        elif skill_name == "system.list_windows":
            return {"filter": ""}
        
        elif skill_name == "system.focus_window":
            for keyword in ["focus", "bring to front", "switch to", "activate"]:
                if keyword in user_input.lower():
                    parts = user_input.lower().split(keyword, 1)
                    if len(parts) > 1:
                        return {"window_title": parts[1].strip()}
            return {"window_title": user_input}
        
        elif skill_name == "system.minimize_window":
            for keyword in ["minimize", "minimise"]:
                if keyword in user_input.lower():
                    parts = user_input.lower().split(keyword, 1)
                    if len(parts) > 1:
                        return {"window_title": parts[1].strip()}
            return {"window_title": user_input}
        
        elif skill_name == "system.maximize_window":
            for keyword in ["maximize", "maximise"]:
                if keyword in user_input.lower():
                    parts = user_input.lower().split(keyword, 1)
                    if len(parts) > 1:
                        return {"window_title": parts[1].strip()}
            return {"window_title": user_input}
        
        elif skill_name == "system.screenshot":
            return {"region": "full"}
        
        elif skill_name == "system.read_screen":
            return {"mode": "ocr", "region": "full"}
        
        elif skill_name == "android.open_app":
            for keyword in ["open on phone", "launch on phone", "open on android", "phone open"]:
                if keyword in user_input.lower():
                    parts = user_input.lower().split(keyword, 1)
                    if len(parts) > 1:
                        return {"package_name": parts[1].strip()}
            return {"package_name": user_input}
        
        elif skill_name == "android.tap":
            # Extract coordinates if present
            import re
            coords = re.findall(r'\d+', user_input)
            if len(coords) >= 2:
                return {"x": int(coords[0]), "y": int(coords[1])}
            return {"x": 0, "y": 0}
        
        elif skill_name == "android.swipe":
            import re
            coords = re.findall(r'\d+', user_input)
            if len(coords) >= 4:
                return {"x1": int(coords[0]), "y1": int(coords[1]), "x2": int(coords[2]), "y2": int(coords[3])}
            return {"x1": 0, "y1": 0, "x2": 0, "y2": 0}
        
        elif skill_name == "android.type_text":
            for keyword in ["type on phone", "type on android", "enter text on phone"]:
                if keyword in user_input.lower():
                    parts = user_input.lower().split(keyword, 1)
                    if len(parts) > 1:
                        return {"text": parts[1].strip()}
            return {"text": user_input}
        
        elif skill_name == "android.get_notifications":
            return {}
        
        elif skill_name == "android.media_control":
            user_lower = user_input.lower()
            if "play" in user_lower:
                return {"action": "play"}
            elif "pause" in user_lower:
                return {"action": "pause"}
            elif "next" in user_lower:
                return {"action": "next"}
            elif "previous" in user_lower or "prev" in user_lower:
                return {"action": "previous"}
            elif "stop" in user_lower:
                return {"action": "stop"}
            return {"action": "play"}
        
        elif skill_name == "android.answer_call":
            return {}
        
        elif skill_name == "android.decline_call":
            return {}
        
        elif skill_name == "android.open_youtube":
            for keyword in ["youtube on phone", "open youtube on phone", "play on youtube phone"]:
                if keyword in user_input.lower():
                    parts = user_input.lower().split(keyword, 1)
                    if len(parts) > 1:
                        return {"query": parts[1].strip()}
            return {"query": ""}
        
        elif skill_name == "android.screenshot":
            return {}
        
        elif skill_name == "android.device_info":
            return {}
        
        return {}