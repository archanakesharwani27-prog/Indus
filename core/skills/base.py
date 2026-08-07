"""
BaseSkill - Abstract base class for all skills
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass


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
    """Complete skill definition."""
    name: str
    description: str
    parameters: List[SkillParameter]
    handler: callable
    category: str = "general"
    requires_confirmation: bool = False
    confirmation_message: Optional[str] = None
    examples: List[str] = None
    
    def __post_init__(self):
        if self.examples is None:
            self.examples = []
    
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


class BaseSkill(ABC):
    """Abstract base class for skills."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique skill name (e.g., 'system.open_app')."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description."""
        pass
    
    @property
    @abstractmethod
    def parameters(self) -> List[SkillParameter]:
        """List of parameter definitions."""
        pass
    
    @property
    def category(self) -> str:
        """Skill category."""
        return "general"
    
    @property
    def requires_confirmation(self) -> bool:
        """Whether this skill requires user confirmation."""
        return False
    
    @property
    def confirmation_message(self) -> Optional[str]:
        """Custom confirmation message."""
        return None
    
    @property
    def examples(self) -> List[str]:
        """Example utterances for this skill."""
        return []
    
    @abstractmethod
    def execute(self, **kwargs) -> Any:
        """Execute the skill with given parameters."""
        pass
    
    def to_definition(self) -> SkillDefinition:
        """Convert to SkillDefinition for registry."""
        return SkillDefinition(
            name=self.name,
            description=self.description,
            parameters=self.parameters,
            handler=self.execute,
            category=self.category,
            requires_confirmation=self.requires_confirmation,
            confirmation_message=self.confirmation_message,
            examples=self.examples,
        )
    
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