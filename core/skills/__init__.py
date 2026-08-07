"""
Skills package - Built-in skills for system, web, communication, etc.
"""

from core.skills.base import BaseSkill, SkillParameter
from core.skills.system import register_system_skills
from core.skills.web import register_web_skills
from core.skills.communication import register_communication_skills
from core.skills.android import register_android_skills
from core.skills.memory import register_memory_skills
from core.skills.vision import register_vision_skills
from core.skills.proactive import register_proactive_skills
from core.skills.agent import register_agent_skills
from core.skills.multiagent import register_multiagent_skills

__all__ = [
    "BaseSkill",
    "SkillParameter",
    "register_system_skills",
    "register_web_skills",
    "register_communication_skills",
    "register_android_skills",
    "register_memory_skills",
    "register_vision_skills",
    "register_proactive_skills",
    "register_agent_skills",
    "register_multiagent_skills",
]