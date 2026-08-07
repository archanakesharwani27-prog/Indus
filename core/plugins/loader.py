"""
PluginLoader - Loads community skills/plugins
"""

import os
import sys
import importlib.util
import inspect
from typing import Dict, Any, List, Optional, Type
from pathlib import Path

from core.skills.base import BaseSkill, SkillDefinition, SkillParameter


class PluginLoader:
    """
    Loads Python plugin files as skills.
    
    Plugin structure:
    my_plugin/
    ├── plugin.json          # Metadata
    └── my_plugin.py         # Contains Skill classes
    
    Or single file:
    my_skill.py              # Contains Skill classes
    """
    
    def __init__(self, plugin_dirs: List[str] = None):
        self.plugin_dirs = plugin_dirs or [
            "plugins",
            os.path.expanduser("~/.indus/plugins"),
            "/usr/share/indus/plugins"
        ]
        self._loaded_plugins: Dict[str, Dict[str, Any]] = {}
        self._skill_classes: Dict[str, Type[BaseSkill]] = {}
    
    def discover_plugins(self) -> List[str]:
        """Discover available plugin files."""
        plugins = []
        for plugin_dir in self.plugin_dirs:
            if not os.path.exists(plugin_dir):
                continue
            
            for item in os.listdir(plugin_dir):
                item_path = os.path.join(plugin_dir, item)
                
                # Python file
                if item.endswith(".py") and not item.startswith("_"):
                    plugins.append(item_path)
                
                # Directory with plugin.json
                elif os.path.isdir(item_path):
                    meta_path = os.path.join(item_path, "plugin.json")
                    if os.path.exists(meta_path):
                        plugins.append(item_path)
        
        return plugins
    
    def load_plugin(self, plugin_path: str) -> Dict[str, Any]:
        """Load a single plugin."""
        if plugin_path in self._loaded_plugins:
            return self._loaded_plugins[plugin_path]
        
        result = {"path": plugin_path, "skills": [], "errors": []}
        
        try:
            if os.path.isdir(plugin_path):
                # Directory plugin - load from plugin.json
                result.update(self._load_directory_plugin(plugin_path))
            else:
                # Single Python file
                result.update(self._load_file_plugin(plugin_path))
            
            # Register skill classes
            for skill_cls in result["skills"]:
                # Create temporary instance to get name property
                temp_instance = skill_cls()
                self._skill_classes[temp_instance.name] = skill_cls
            
            self._loaded_plugins[plugin_path] = result
            
        except Exception as e:
            result["errors"].append(str(e))
        
        return result
    
    def _load_directory_plugin(self, plugin_dir: str) -> Dict[str, Any]:
        """Load plugin from directory with plugin.json."""
        import json
        
        meta_path = os.path.join(plugin_dir, "plugin.json")
        with open(meta_path) as f:
            metadata = json.load(f)
        
        # Find main Python file
        main_file = metadata.get("main", "plugin.py")
        main_path = os.path.join(plugin_dir, main_file)
        
        if not os.path.exists(main_path):
            # Try to find any .py file
            for f in os.listdir(plugin_dir):
                if f.endswith(".py"):
                    main_path = os.path.join(plugin_dir, f)
                    break
        
        if os.path.exists(main_path):
            return self._load_file_plugin(main_path, metadata)
        
        return {"skills": [], "errors": ["No Python file found"], "metadata": metadata}
    
    def _load_file_plugin(self, file_path: str, metadata: Dict = None) -> Dict[str, Any]:
        """Load plugin from Python file."""
        # Load module
        module_name = f"indus_plugin_{os.path.basename(file_path).replace('.py', '')}"
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        
        # Find Skill classes
        skills = []
        for name, obj in inspect.getmembers(module):
            if (inspect.isclass(obj) and 
                issubclass(obj, BaseSkill) and 
                obj != BaseSkill):
                skills.append(obj)
        
        return {
            "skills": skills,
            "errors": [],
            "metadata": metadata or {}
        }
    
    def load_all_plugins(self) -> List[Dict[str, Any]]:
        """Load all discovered plugins."""
        results = []
        for plugin_path in self.discover_plugins():
            results.append(self.load_plugin(plugin_path))
        return results
    
    def get_skill_class(self, name: str) -> Optional[Type[BaseSkill]]:
        """Get loaded skill class by name."""
        return self._skill_classes.get(name)
    
    def create_skill_instance(self, name: str) -> Optional[BaseSkill]:
        """Create skill instance by name."""
        cls = self.get_skill_class(name)
        if cls:
            return cls()
        return None
    
    def get_all_skills(self) -> List[BaseSkill]:
        """Get instances of all loaded skills."""
        return [cls() for cls in self._skill_classes.values()]


# Global instance
_plugin_loader: Optional[PluginLoader] = None


def get_plugin_loader(plugin_dirs: List[str] = None) -> PluginLoader:
    """Get global plugin loader."""
    global _plugin_loader
    if _plugin_loader is None:
        _plugin_loader = PluginLoader(plugin_dirs)
    return _plugin_loader