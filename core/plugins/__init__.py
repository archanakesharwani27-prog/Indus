"""
Plugins Package - Plugin system for community skills
"""

from core.plugins.loader import PluginLoader, get_plugin_loader

__all__ = [
    "PluginLoader",
    "get_plugin_loader",
]