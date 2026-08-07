"""
SkillRegistry - Discoverable skill registration and management
"""

from typing import Dict, List, Any, Callable, Optional
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import inspect


@dataclass
class SkillParameter:
    """Skill parameter definition."""
    name: str
    type: str  # "string", "number", "boolean", "array", "object"
    description: str
    required: bool = True
    default: Any = None
    enum: Optional[List[str]] = None


@dataclass
class SkillDefinition:
    """Complete skill definition for registry and LLM function calling."""
    name: str
    description: str
    parameters: List[SkillParameter]
    handler: Callable
    category: str = "general"
    requires_confirmation: bool = False
    examples: List[str] = field(default_factory=list)
    
    def to_openai_function(self) -> Dict[str, Any]:
        """Convert to OpenAI function calling format."""
        properties = {}
        required = []
        
        for param in self.parameters:
            prop = {
                "type": param.type,
                "description": param.description,
            }
            if param.enum:
                prop["enum"] = param.enum
            if param.default is not None:
                prop["default"] = param.default
            
            properties[param.name] = prop
            
            if param.required:
                required.append(param.name)
        
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }


class SkillRegistry:
    """Registry for managing and discovering skills."""
    
    def __init__(self):
        self._skills: Dict[str, SkillDefinition] = {}
        self._categories: Dict[str, List[str]] = {}
    
    def register(self, skill: SkillDefinition) -> None:
        """Register a skill."""
        if skill.name in self._skills:
            print(f"Warning: Overwriting existing skill '{skill.name}'")
        
        self._skills[skill.name] = skill
        
        if skill.category not in self._categories:
            self._categories[skill.category] = []
        self._categories[skill.category].append(skill.name)
    
    def unregister(self, skill_name: str) -> bool:
        """Unregister a skill."""
        if skill_name in self._skills:
            skill = self._skills.pop(skill_name)
            if skill.category in self._categories:
                self._categories[skill.category].remove(skill_name)
            return True
        return False
    
    def get(self, skill_name: str) -> Optional[SkillDefinition]:
        """Get skill by name."""
        return self._skills.get(skill_name)
    
    def get_skill(self, skill_name: str) -> Optional[SkillDefinition]:
        """Alias for get()."""
        return self.get(skill_name)
    
    def list_skills(self, category: Optional[str] = None) -> List[SkillDefinition]:
        """List all skills, optionally filtered by category."""
        if category:
            skill_names = self._categories.get(category, [])
            return [self._skills[name] for name in skill_names if name in self._skills]
        return list(self._skills.values())
    
    def get_categories(self) -> List[str]:
        """Get all skill categories."""
        return list(self._categories.keys())
    
    def get_schemas(self) -> List[Dict[str, Any]]:
        """Get all skill schemas for LLM function calling."""
        return [skill.to_openai_function() for skill in self._skills.values()]
    
    def execute(self, skill_name: str, **kwargs) -> Any:
        """Execute a skill by name with arguments."""
        skill = self.get(skill_name)
        if not skill:
            raise ValueError(f"Skill not found: {skill_name}")
        
        # Validate required parameters
        for param in skill.parameters:
            if param.required and param.name not in kwargs:
                if param.default is not None:
                    kwargs[param.name] = param.default
                else:
                    raise ValueError(f"Missing required parameter: {param.name}")
        
        return skill.handler(**kwargs)
    
    def __contains__(self, skill_name: str) -> bool:
        return skill_name in self._skills
    
    def __len__(self) -> int:
        return len(self._skills)


# Global registry instance
_global_registry = SkillRegistry()


def get_registry() -> SkillRegistry:
    """Get the global skill registry."""
    return _global_registry


def register_skill(skill: SkillDefinition) -> None:
    """Register a skill in the global registry."""
    _global_registry.register(skill)


def skill(
    name: str,
    description: str,
    parameters: List[SkillParameter],
    category: str = "general",
    requires_confirmation: bool = False,
    examples: List[str] = None,
):
    """
    Decorator for registering skills.
    
    Usage:
        @skill(
            name="system.open_app",
            description="Open an application",
            parameters=[
                SkillParameter("app_name", "string", "Name of the app to open"),
            ],
            category="system",
        )
        def open_app(app_name: str):
            ...
    """
    def decorator(func: Callable) -> Callable:
        skill_def = SkillDefinition(
            name=name,
            description=description,
            parameters=parameters,
            handler=func,
            category=category,
            requires_confirmation=requires_confirmation,
            examples=examples or [],
        )
        _global_registry.register(skill_def)
        return func
    return decorator