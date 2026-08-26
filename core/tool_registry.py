# core/tool_registry.py
"""
INDUS Canonical Tool Registry
==============================
Single source of truth for all 33 registered tools.

Both `main.py._execute_tool()` and `agent_loop._dispatch_tool_action()` use
this registry so the capability surface is identical regardless of how a
request enters the system (Gemini Live voice, text command, or agent_task).

Each entry defines a uniform call adapter:

    handler(parameters: dict, player: Any) -> Any

The handler is responsible for:
  - Extracting the correct kwargs from `parameters`
  - Calling the underlying tool function
  - Returning a raw string or dict result (normalize_result() is applied downstream)

No tool implementation is duplicated here -- only import + call wiring.
"""

from __future__ import annotations
from typing import Any, Callable, Dict

# -----------------------------------------------------------------------------
# Registry type:  { tool_name: handler(parameters, player) -> Any }
# -----------------------------------------------------------------------------
_REGISTRY: Dict[str, Callable] = {}


def _reg(name: str):
    """Decorator that registers a handler under `name`."""
    def _decorator(fn: Callable) -> Callable:
        _REGISTRY[name] = fn
        return fn
    return _decorator


# -- OS / App Control ----------------------------------------------------------

@_reg("open_app")
def _open_app(parameters: dict, player: Any):
    from actions.open_app import open_app
    return open_app(parameters=parameters, player=player)


@_reg("computer_control")
def _computer_control(parameters: dict, player: Any):
    from actions.computer_control import computer_control
    return computer_control(parameters=parameters, player=player)


@_reg("computer_settings")
def _computer_settings(parameters: dict, player: Any):
    from actions.computer_settings import computer_settings
    return computer_settings(parameters=parameters, player=player)


@_reg("desktop_control")
def _desktop_control(parameters: dict, player: Any):
    from actions.desktop import desktop_control
    return desktop_control(parameters=parameters, player=player)


# -- Vision / Screen -----------------------------------------------------------

@_reg("screen_understand")
def _screen_understand(parameters: dict, player: Any):
    from actions.vision_engine import screen_understand
    return screen_understand(query=parameters.get("query", "What is on screen?"), player=player)


@_reg("vision_find_element")
def _vision_find_element(parameters: dict, player: Any):
    from actions.vision_engine import ground_ui_element
    import json
    result = ground_ui_element(
        target_description=parameters.get("target") or parameters.get("description", ""),
        context=parameters.get("context", ""),
        player=player,
    )
    return json.dumps(result) if isinstance(result, dict) else result


@_reg("vision_click")
def _vision_click(parameters: dict, player: Any):
    from actions.vision_engine import vision_click
    return vision_click(
        target=parameters.get("target") or parameters.get("description", ""),
        context=parameters.get("context", ""),
        player=player,
    )


@_reg("vision_type")
def _vision_type(parameters: dict, player: Any):
    from actions.vision_engine import vision_type
    return vision_type(
        target=parameters.get("target") or parameters.get("field", ""),
        text=parameters.get("text") or parameters.get("query", ""),
        press_enter=parameters.get("press_enter", True),
        clear_first=parameters.get("clear_first", True),
        context=parameters.get("context", ""),
        player=player,
    )


@_reg("vision_scroll")
def _vision_scroll(parameters: dict, player: Any):
    from actions.vision_engine import vision_scroll
    return vision_scroll(
        direction=parameters.get("direction", "down"),
        amount=parameters.get("amount", 300),
        target=parameters.get("target"),
        player=player,
    )


@_reg("vision_engine")
def _vision_engine(parameters: dict, player: Any):
    from actions.vision_engine import vision_engine
    return vision_engine(parameters=parameters, player=player)


@_reg("screen_process")
def _screen_process(parameters: dict, player: Any):
    from actions.screen_processor import screen_process
    return screen_process(parameters=parameters, player=player)


# -- File System ---------------------------------------------------------------

@_reg("file_controller")
def _file_controller(parameters: dict, player: Any):
    from actions.file_controller import file_controller
    return file_controller(parameters=parameters, player=player)


@_reg("file_processor")
def _file_processor(parameters: dict, player: Any, speak=None):
    from actions.file_processor import file_processor
    return file_processor(parameters=parameters, player=player, speak=speak)


# -- Web / Research ------------------------------------------------------------

@_reg("web_search")
def _web_search(parameters: dict, player: Any):
    from actions.web_search import web_search_action
    return web_search_action(parameters=parameters, player=player)


@_reg("deep_research")
def _deep_research(parameters: dict, player: Any):
    from actions.deep_research import deep_research
    return deep_research(
        query=parameters.get("query", ""),
        domain=parameters.get("domain", "general"),
        player=player,
    )


@_reg("weather_report")
def _weather_report(parameters: dict, player: Any):
    from actions.weather_report import weather_action
    return weather_action(parameters=parameters, player=player)


@_reg("browser_control")
def _browser_control(parameters: dict, player: Any):
    from actions.browser_control import browser_control
    return browser_control(parameters=parameters, player=player)


@_reg("youtube_video")
def _youtube_video(parameters: dict, player: Any):
    from actions.youtube_video import youtube_video
    return youtube_video(parameters=parameters, player=player)


@_reg("flight_finder")
def _flight_finder(parameters: dict, player: Any):
    from actions.flight_finder import flight_finder
    return flight_finder(parameters=parameters, player=player)


# -- Communication -------------------------------------------------------------

@_reg("send_message")
def _send_message(parameters: dict, player: Any):
    from actions.send_message import send_message
    return send_message(parameters=parameters, player=player)


@_reg("reminder")
def _reminder(parameters: dict, player: Any):
    from actions.reminder import reminder
    return reminder(parameters=parameters, player=player)


# -- Developer Tools -----------------------------------------------------------

@_reg("code_helper")
def _code_helper(parameters: dict, player: Any, speak=None):
    from actions.code_helper import code_helper
    return code_helper(parameters=parameters, player=player, speak=speak)


@_reg("dev_agent")
def _dev_agent(parameters: dict, player: Any, speak=None):
    from actions.dev_agent import dev_agent
    return dev_agent(parameters=parameters, player=player, speak=speak)


@_reg("git_controller")
def _git_controller(parameters: dict, player: Any):
    from actions.git_controller import git_controller
    return git_controller(parameters=parameters, player=player)


@_reg("terminal_command")
def _terminal_command(parameters: dict, player: Any):
    from actions.git_controller import terminal_command
    return terminal_command(
        command=parameters.get("command", ""),
        cwd=parameters.get("cwd", ""),
        timeout=parameters.get("timeout", 30),
    )


# -- Hardware / Peripheral -----------------------------------------------------

@_reg("mobile_bridge")
def _mobile_bridge(parameters: dict, player: Any):
    from actions.mobile_bridge import mobile_bridge
    return mobile_bridge(parameters=parameters, player=player)


@_reg("bluetooth_control")
def _bluetooth_control(parameters: dict, player: Any):
    from actions.bluetooth_controller import bluetooth_control
    return bluetooth_control(
        action=parameters.get("action", ""),
        device_name=parameters.get("device_name", ""),
    )


@_reg("smart_home")
def _smart_home(parameters: dict, player: Any):
    from actions.smart_home import smart_home
    return smart_home(parameters=parameters, player=player)


# -- Media / Entertainment -----------------------------------------------------

@_reg("stream_content")
def _stream_content(parameters: dict, player: Any):
    from actions.media_streamer import stream_content
    return stream_content(parameters=parameters, player=player)


@_reg("game_updater")
def _game_updater(parameters: dict, player: Any, speak=None):
    from actions.game_updater import game_updater
    return game_updater(parameters=parameters, player=player, speak=speak)


@_reg("universal_ad_skipper")
def _universal_ad_skipper(parameters: dict, player: Any, speak=None):
    from actions.universal_ad_skipper import universal_ad_skipper
    return universal_ad_skipper(parameters=parameters, player=player, speak=speak)


@_reg("app_settings_navigator")
def _app_settings_navigator(parameters: dict, player: Any, speak=None):
    from actions.app_ui_navigator import app_settings_navigator
    return app_settings_navigator(parameters=parameters, player=player, speak=speak)


@_reg("video_editor")
def _video_editor(parameters: dict, player: Any, speak=None):
    from actions.video_editor import video_editor
    return video_editor(parameters=parameters, player=player, speak=speak)


@_reg("image_generator")
def _image_generator(parameters: dict, player: Any, speak=None):
    from actions.image_generator import image_generator
    return image_generator(parameters=parameters, player=player, speak=speak)


@_reg("smart_downloader")
def _smart_downloader(parameters: dict, player: Any, speak=None):
    from actions.smart_downloader import smart_downloader
    return smart_downloader(parameters=parameters, player=player, speak=speak)


@_reg("app_installer")
def _app_installer(parameters: dict, player: Any, speak=None):
    from actions.app_installer import app_installer
    return app_installer(parameters=parameters, player=player, speak=speak)


# -- Shopping ------------------------------------------------------------------

@_reg("search_and_show_products")
def _search_products(parameters: dict, player: Any):
    from actions.shopping_assistant import search_and_show_products
    return search_and_show_products(parameters=parameters, player=player)


@_reg("proceed_to_cart_and_checkout")
def _checkout(parameters: dict, player: Any):
    from actions.shopping_assistant import proceed_to_cart_and_checkout
    return proceed_to_cart_and_checkout(
        product_url=parameters.get("product_url", ""),
        size=parameters.get("size", ""),
        player=player,
    )


@_reg("save_shopping_preference")
def _save_shopping_pref(parameters: dict, player: Any):
    from actions.shopping_assistant import save_shopping_preference
    return save_shopping_preference(
        key=parameters.get("key", ""),
        value=parameters.get("value", ""),
    )


@_reg("save_media_source_preference")
def _save_media_pref(parameters: dict, player: Any):
    from actions.media_streamer import save_media_source_preference
    return save_media_source_preference(
        keyword_or_title=parameters.get("keyword_or_title", ""),
        url_or_platform=parameters.get("url_or_platform", ""),
    )


# -- Workspace -----------------------------------------------------------------

@_reg("live_writer")
def _live_writer(parameters: dict, player: Any):
    from actions.live_writer import live_writer
    return live_writer(parameters=parameters, player=player)


@_reg("teleport_workspace")
def _teleport_workspace(parameters: dict, player: Any):
    from actions.workspace_teleport import teleport_workspace
    return teleport_workspace(
        layout=parameters.get("layout", "split_dev"),
        player=player,
    )


# -- System / Security ---------------------------------------------------------

@_reg("system_radar")
def _system_radar(parameters: dict, player: Any):
    from actions.system_radar import system_radar
    return system_radar(parameters=parameters, player=player)


@_reg("security_protocols")
def _security_protocols(parameters: dict, player: Any):
    from actions.security_protocols import security_protocols
    return security_protocols(parameters=parameters, player=player)


@_reg("security_vault")
def _security_vault(parameters: dict, player: Any):
    from core.security_vault import security_vault
    return security_vault(parameters=parameters, player=player)


# -- Memory & Long-term Conversation History -----------------------------------

@_reg("search_conversation_history")
def _search_conversation_history(parameters: dict, player: Any):
    from memory.memory_manager import search_conversation_history
    return search_conversation_history(
        query=parameters.get("query", ""),
        limit=parameters.get("limit", 15),
    )


@_reg("recall_memory")
def _recall_memory(parameters: dict, player: Any):
    from memory.memory_manager import recall_memory
    return recall_memory(
        query=parameters.get("query", ""),
        category=parameters.get("category", ""),
    )


# Legacy aliases present in older agent_loop plans
@_reg("cmd_control")
def _cmd_control(parameters: dict, player: Any):
    from actions.git_controller import terminal_command
    return terminal_command(
        command=parameters.get("task") or parameters.get("command", ""),
        cwd=parameters.get("cwd", ""),
        timeout=30,
    )


@_reg("desktop_control")
def _desktop_control_alias(parameters: dict, player: Any):
    from actions.desktop import desktop_control
    return desktop_control(parameters=parameters, player=player)


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------

# Tools that accept an optional speak= callback (used by dispatch_with_speak)
_SPEAK_TOOLS: set = {
    "code_helper", "dev_agent", "game_updater", "universal_ad_skipper",
    "app_settings_navigator", "video_editor", "image_generator",
    "smart_downloader", "app_installer", "file_processor",
}


def get_handler(tool_name: str):
    """Return the handler callable for `tool_name`, or None if not registered."""
    return _REGISTRY.get(tool_name)


def dispatch(tool_name: str, parameters: dict, player=None):
    """
    Dispatch a tool call through the canonical registry.

    Returns (result, error_str).
      result    -- raw tool output (str, dict, or None)
      error_str -- None on success, error message on failure / not found
    """
    handler = _REGISTRY.get(tool_name)
    if handler is None:
        return None, f"Tool '{tool_name}' is not registered in the canonical registry."
    try:
        result = handler(parameters or {}, player)
        return result, None
    except Exception as exc:
        return None, str(exc)


def dispatch_with_speak(tool_name: str, parameters: dict, player=None, speak=None):
    """
    Dispatch a tool call through the canonical registry, passing the speak
    callback to tools that support it (code_helper, dev_agent, etc.).

    Returns (result, error_str).
    """
    handler = _REGISTRY.get(tool_name)
    if handler is None:
        return None, f"Tool '{tool_name}' is not registered in the canonical registry."
    try:
        if tool_name in _SPEAK_TOOLS and speak is not None:
            result = handler(parameters or {}, player, speak=speak)
        else:
            result = handler(parameters or {}, player)
        return result, None
    except Exception as exc:
        return None, str(exc)


def all_tool_names() -> list:
    """Return sorted list of all registered tool names."""
    return sorted(_REGISTRY.keys())


def tool_count() -> int:
    return len(_REGISTRY)
