"""
System package - Windows system control modules
"""

from core.system.launcher import AppLauncher, get_launcher
from core.system.windows import WindowManager, WindowInfo, get_window_manager
from core.system.shell import ShellExecutor, CommandResult, get_shell_executor
from core.system.screen import ScreenAnalyzer, ScreenRegion, get_screen_analyzer

__all__ = [
    "AppLauncher",
    "get_launcher",
    "WindowManager",
    "WindowInfo",
    "get_window_manager",
    "ShellExecutor",
    "CommandResult",
    "get_shell_executor",
    "ScreenAnalyzer",
    "ScreenRegion",
    "get_screen_analyzer",
]