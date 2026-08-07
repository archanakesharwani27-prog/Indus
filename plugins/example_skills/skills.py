"""
Example custom skills plugin for Indus.
Place in plugins/example_skills/ and it will be auto-discovered.
"""

from typing import List
from core.skills.base import BaseSkill, SkillParameter


class CustomCalcSkill(BaseSkill):
    """Custom calculator skill with history."""
    
    @property
    def name(self) -> str:
        return "custom.calc"
    
    @property
    def description(self) -> str:
        return "Advanced calculator with history and constants"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="expression",
                type="string",
                description="Math expression to evaluate",
                required=True,
            ),
            SkillParameter(
                name="use_history",
                type="boolean",
                description="Use previous result as 'ans'",
                required=False,
                default=True,
            ),
        ]
    
    @property
    def category(self) -> str:
        return "custom"
    
    @property
    def examples(self) -> List[str]:
        return [
            "Calculate 2 + 2",
            "Calculate sqrt(16) * pi",
            "Calculate ans * 2",
        ]
    
    def __init__(self):
        super().__init__()
        self._history = []
        self._last_result = 0
    
    def execute(self, expression: str, use_history: bool = True) -> str:
        try:
            # Replace 'ans' with last result
            if use_history and "ans" in expression.lower():
                expression = expression.replace("ans", str(self._last_result))
            
            # Safe eval with math functions
            import math
            allowed = {
                "abs": abs, "round": round, "min": min, "max": max,
                "sum": sum, "pow": pow,
                "sin": math.sin, "cos": math.cos, "tan": math.tan,
                "sqrt": math.sqrt, "log": math.log, "exp": math.exp,
                "pi": math.pi, "e": math.e,
                "ans": self._last_result
            }
            
            result = eval(expression, {"__builtins__": {}}, allowed)
            self._last_result = result
            self._history.append({"expr": expression, "result": result})
            
            # Keep last 10
            if len(self._history) > 10:
                self._history.pop(0)
            
            return f"Result: {result}"
        except Exception as e:
            return f"Calculation error: {e}"


class WeatherSkill(BaseSkill):
    """Weather skill (mock implementation)."""
    
    @property
    def name(self) -> str:
        return "custom.weather"
    
    @property
    def description(self) -> str:
        return "Get weather for a location (mock)"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="location",
                type="string",
                description="City name",
                required=True,
            ),
            SkillParameter(
                name="unit",
                type="string",
                description="Temperature unit",
                required=False,
                default="celsius",
                enum=["celsius", "fahrenheit"],
            ),
        ]
    
    @property
    def category(self) -> str:
        return "custom"
    
    @property
    def examples(self) -> List[str]:
        return [
            "Weather in Mumbai",
            "Weather in Delhi fahrenheit",
        ]
    
    def execute(self, location: str, unit: str = "celsius") -> str:
        # Mock weather data
        import random
        temp_c = random.randint(20, 35)
        conditions = ["Sunny", "Cloudy", "Rainy", "Partly Cloudy"]
        
        if unit == "fahrenheit":
            temp = temp_c * 9/5 + 32
            unit_str = "°F"
        else:
            temp = temp_c
            unit_str = "°C"
        
        return f"Weather in {location}: {random.choice(conditions)}, {temp:.0f}{unit_str}"


class TimerSkill(BaseSkill):
    """Timer/stopwatch skill."""
    
    @property
    def name(self) -> str:
        return "custom.timer"
    
    @property
    def description(self) -> str:
        return "Set timers and stopwatches"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="action",
                type="string",
                description="Action: 'start', 'stop', 'status', 'set'",
                required=True,
                enum=["start", "stop", "status", "set"],
            ),
            SkillParameter(
                name="duration",
                type="string",
                description="Duration for 'set' (e.g., '5m', '1h', '30s')",
                required=False,
                default="",
            ),
            SkillParameter(
                name="label",
                type="string",
                description="Timer label",
                required=False,
                default="Timer",
            ),
        ]
    
    @property
    def category(self) -> str:
        return "custom"
    
    @property
    def examples(self) -> List[str]:
        return [
            "Set timer for 5 minutes",
            "Start timer",
            "Stop timer",
            "Timer status",
        ]
    
    def __init__(self):
        super().__init__()
        self._timers = {}  # label -> {start, duration, running}
    
    def execute(self, action: str, duration: str = "", label: str = "Timer") -> str:
        import time
        
        if action == "set":
            if not duration:
                return "Duration required for set action"
            
            # Parse duration (e.g., "5m", "1h30m", "30s")
            seconds = self._parse_duration(duration)
            if seconds <= 0:
                return "Invalid duration"
            
            self._timers[label] = {
                "start": time.time(),
                "duration": seconds,
                "running": True
            }
            return f"Timer '{label}' set for {duration}"
        
        elif action == "start":
            if label not in self._timers:
                return f"Timer '{label}' not set. Use 'set' first."
            self._timers[label]["running"] = True
            self._timers[label]["start"] = time.time()
            return f"Timer '{label}' started"
        
        elif action == "stop":
            if label not in self._timers:
                return f"Timer '{label}' not found"
            self._timers[label]["running"] = False
            return f"Timer '{label}' stopped"
        
        elif action == "status":
            if label not in self._timers:
                return f"Timer '{label}' not found"
            
            timer = self._timers[label]
            elapsed = time.time() - timer["start"] if timer["running"] else timer.get("elapsed", 0)
            remaining = max(0, timer["duration"] - elapsed)
            
            status = "Running" if timer["running"] else "Paused"
            return (f"Timer '{label}': {status}\n"
                   f"  Elapsed: {self._format_time(elapsed)}\n"
                   f"  Remaining: {self._format_time(remaining)}")
        
        return f"Unknown action: {action}"
    
    def _parse_duration(self, duration: str) -> int:
        """Parse duration string to seconds."""
        import re
        total = 0
        for match in re.finditer(r'(\d+)([hms])', duration.lower()):
            val, unit = int(match.group(1)), match.group(2)
            if unit == 'h':
                total += val * 3600
            elif unit == 'm':
                total += val * 60
            elif unit == 's':
                total += val
        return total
    
    def _format_time(self, seconds: float) -> str:
        """Format seconds as H:M:S."""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        if h > 0:
            return f"{h}h {m}m {s}s"
        elif m > 0:
            return f"{m}m {s}s"
        return f"{s}s"