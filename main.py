import asyncio
import threading
import json
import sys
import time
import re
import traceback
from pathlib import Path

import sounddevice as sd
from google import genai
from google.genai import types
from ui import JarvisUI
from memory.memory_manager import (
    load_memory, update_memory, format_memory_for_prompt,
    should_extract_memory, extract_memory
)

from actions.file_processor import file_processor
from actions.flight_finder     import flight_finder
from actions.open_app          import open_app
from actions.weather_report    import weather_action
from actions.send_message      import send_message
from actions.reminder          import reminder
from actions.computer_settings import computer_settings
from actions.vision_engine     import (
    vision_click, vision_type, vision_scroll, vision_engine,
    ground_ui_element, screen_understand
)
from actions.desktop           import desktop_control
from actions.browser_control   import browser_control
from actions.file_controller   import file_controller
from actions.code_helper       import code_helper
from actions.dev_agent         import dev_agent
from actions.web_search        import web_search as web_search_action
from actions.computer_control  import computer_control
from actions.game_updater      import game_updater
from actions.git_controller    import git_controller, terminal_command
from actions.system_radar      import system_radar
from actions.smart_home        import smart_home
from actions.security_protocols import security_protocols
from actions.media_streamer    import stream_content, save_media_source_preference
from actions.shopping_assistant import search_and_show_products, proceed_to_cart_and_checkout, save_shopping_preference
from actions.bluetooth_controller import bluetooth_control
from actions.deep_research        import deep_research
from actions.mobile_bridge        import mobile_bridge
from actions.live_writer          import live_writer
from actions.workspace_teleport   import teleport_workspace
from actions.universal_ad_skipper import universal_ad_skipper
from actions.app_ui_navigator     import app_settings_navigator
from actions.video_editor         import video_editor
from actions.image_generator      import image_generator
from actions.smart_downloader     import smart_downloader
from actions.app_installer        import app_installer
from core.security_vault          import security_vault
from core.security_engine         import security_engine
from core.code_sandbox            import handle_unknown_tool_replan
from core.audit_logger            import audit_logger
from core.cancellation            import cancellation_manager, is_stop_phrase
from core.event_bus               import event_bus, E
from core.tool_result             import ToolResult, normalize_result
from actions.wake_word            import wake_word_controller, is_standby_phrase, matches_wake_word
from core.avatar.audio            import compute_pcm_rms






def get_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


BASE_DIR        = get_base_dir()
API_CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"
PROMPT_PATH     = BASE_DIR / "core" / "prompt.txt"
LIVE_MODEL          = "models/gemini-2.5-flash-native-audio-preview-12-2025"
CHANNELS            = 1
SEND_SAMPLE_RATE    = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE          = 1024


def _prompt_for_api_key() -> str:
    """Prompt the user with a sleek Qt dialog on first launch to enter their Gemini API key."""
    try:
        from PyQt6.QtWidgets import QApplication, QInputDialog, QLineEdit
        app = QApplication.instance() or QApplication(sys.argv)
        key, ok = QInputDialog.getText(
            None,
            "INDUS — First Launch Setup",
            "Welcome to INDUS AI Assistant!\n\nPlease enter your Google Gemini API Key:\n(Get your free key at https://aistudio.google.com/)",
            QLineEdit.EchoMode.Normal,
            ""
        )
        if ok and key.strip():
            api_key = key.strip()
            API_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            existing = {}
            if API_CONFIG_PATH.exists():
                try:
                    with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
                        existing = json.load(f)
                except Exception:
                    existing = {}
            existing["gemini_api_key"] = api_key
            if "os_system" not in existing:
                existing["os_system"] = "windows"
            with open(API_CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(existing, f, indent=4)
            print(f"[INDUS] Gemini API key saved to {API_CONFIG_PATH}")
            return api_key
    except Exception as e:
        print(f"[INDUS] GUI Prompt error: {e}")
    return ""


def _get_api_key() -> str:
    """Load Gemini API key. Prompts user interactively on first launch if missing."""
    key = ""
    try:
        if API_CONFIG_PATH.exists():
            with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            key = data.get("gemini_api_key", "").strip()
    except Exception:
        key = ""

    # If key is missing, prompt user with interactive GUI dialog
    if not key:
        key = _prompt_for_api_key()

    if not key:
        _show_startup_error(
            "Gemini API Key Required",
            "INDUS requires a Gemini API key to operate.\n\n"
            "You can get a free API key at:\nhttps://aistudio.google.com/\n\n"
            "Please restart INDUS and enter your key when prompted."
        )
        sys.exit(1)

    return key


def _show_startup_error(title: str, message: str) -> None:
    """Display a startup error in both console and a Qt dialog box."""
    print(f"\n[INDUS STARTUP ERROR] {title}\n{message}\n")
    try:
        from PyQt6.QtWidgets import QApplication, QMessageBox
        app = QApplication.instance() or QApplication(sys.argv)
        box = QMessageBox()
        box.setWindowTitle(f"INDUS — {title}")
        box.setText(message)
        box.setIcon(QMessageBox.Icon.Critical)
        box.exec()
    except Exception:
        pass  # Console output already printed above


def _load_system_prompt() -> str:
    try:
        return PROMPT_PATH.read_text(encoding="utf-8")
    except Exception:
        return (
            "You are JARVIS, Tony Stark's AI assistant. "
            "Be concise, direct, and always use the provided tools to complete tasks. "
            "Never simulate or guess results -- always call the appropriate tool."
        )
    
_last_memory_input = ""

def _update_memory_async(user_text: str, jarvis_text: str, intent: str = "") -> None:
    global _last_memory_input

    user_text   = (user_text   or "").strip()
    jarvis_text = (jarvis_text or "").strip()

    # Always save if there's meaningful user input (removed length > 5 gate)
    if not user_text or user_text == _last_memory_input:
        return
    _last_memory_input = user_text

    # 1. Permanently record every conversation turn to SQLite (unconditional)
    try:
        from memory.db_engine import db_save_conversation
        db_save_conversation(user_text, jarvis_text, intent=intent)
    except Exception as e:
        print(f"[Memory] DB log error: {e}")

    # 2. Extract facts, habits, and preferences (keyword-only, fast path)
    try:
        api_key = _get_api_key()
        if should_extract_memory(user_text, jarvis_text, api_key):
            data = extract_memory(user_text, jarvis_text, api_key)
            if data:
                update_memory(data)
                print(f"[Memory] [OK] Learned & Persisted: {list(data.keys())}")
    except Exception as e:
        if "429" not in str(e):
            print(f"[Memory] [WARN] {e}")

TOOL_DECLARATIONS = [
    {
        "name": "open_app",
        "description": (
            "Opens any application on the Windows computer. "
            "Use this whenever the user asks to open, launch, or start any app, "
            "website, or program. Always call this tool -- never just say you opened it."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "app_name": {
                    "type": "STRING",
                    "description": "Exact name of the application (e.g. 'WhatsApp', 'Chrome', 'Spotify')"
                }
            },
            "required": ["app_name"]
        }
    },
    {
        "name": "web_search",
        "description": (
            "Searches the web for recent internet articles or specific online queries. "
            "DO NOT call this for basic general knowledge, definitions, math, or well-known facts "
            "(e.g. who is PM, full forms like NASA/ISRO, capitals, translations) -- answer general knowledge directly."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query":  {"type": "STRING", "description": "Search query"},
                "mode":   {"type": "STRING", "description": "search (default) or compare"},
                "items":  {"type": "ARRAY", "items": {"type": "STRING"}, "description": "Items to compare"},
                "aspect": {"type": "STRING", "description": "price | specs | reviews"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "weather_report",
        "description": "Gives the weather report to user",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "city": {"type": "STRING", "description": "City name"}
            },
            "required": ["city"]
        }
    },
    {
        "name": "send_message",
        "description": (
            "Sends a text message, sends a screenshot, OR initiates a voice/video call via WhatsApp or Telegram. "
            "When user says 'call <person>' or '<person> ko call karo on whatsapp': set action='call' or 'voice_call'. "
            "When user says 'video call <person>': set action='video_call'. "
            "When user says 'send screenshot to <person>': set send_screenshot=True. "
            "For normal text messages: set message_text."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "receiver":        {"type": "STRING",  "description": "Recipient contact name"},
                "message_text":    {"type": "STRING",  "description": "The text message to send (leave empty for call or screenshot)"},
                "platform":        {"type": "STRING",  "description": "Platform: WhatsApp, Telegram, Instagram, etc. Default: WhatsApp"},
                "action":          {"type": "STRING",  "description": "Action type: 'send' (default), 'call' / 'voice_call', 'video_call', 'send_screenshot'"},
                "send_screenshot": {"type": "BOOLEAN", "description": "If True, take a screenshot and send it as an image"},
                "caption":         {"type": "STRING",  "description": "Optional caption to add alongside the screenshot"},
            },
            "required": ["receiver", "platform"]
        }
    },
    {
        "name": "reminder",
        "description": "Sets a timed reminder using Windows Task Scheduler.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "date":    {"type": "STRING", "description": "Date in YYYY-MM-DD format"},
                "time":    {"type": "STRING", "description": "Time in HH:MM format (24h)"},
                "message": {"type": "STRING", "description": "Reminder message text"}
            },
            "required": ["date", "time", "message"]
        }
    },
    {
        "name": "youtube_video",
        "description": (
            "Controls YouTube. Use for: playing videos, auto-skipping ads, changing video quality "
            "(e.g. 1080p, 720p, 480p, 360p, auto), adjusting playback speed, pausing, stopping, "
            "closing YouTube, muting, getting info, summarizing, or trending videos. "
            "When user wants to set video quality: use action='set_quality' with quality='360p'|'720p'|'1080p'|'auto'. "
            "When user wants to change speed: use action='set_speed' with speed='1.25x'|'1.5x'|'2x'|'0.5x'. "
            "When user wants to play a song/video: use action='play'. "
            "When user wants to play and skip ads: use action='play_and_skip_ad'. "
            "When user says stop, pause, unpause, close, mute or fullscreen: use action='stop'|'pause'|'resume'|'close'|'mute'|'fullscreen'."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":  {"type": "STRING", "description": "play | play_and_skip_ad | stop | pause | resume | close | mute | fullscreen | set_quality | set_speed | summarize | get_info | trending"},
                "query":   {"type": "STRING", "description": "Search query for play action"},
                "quality": {"type": "STRING", "description": "Video resolution: '360p' | '480p' | '720p' | '1080p' | 'auto'"},
                "speed":   {"type": "STRING", "description": "Playback speed: '1.25x' | '1.5x' | '2x' | '0.5x' | 'normal'"},
                "save":    {"type": "BOOLEAN", "description": "Save summary to Notepad (summarize only)"},
                "region":  {"type": "STRING", "description": "Country code for trending e.g. IN, US"},
                "url":     {"type": "STRING", "description": "Video URL for get_info action"},
            },
            "required": []
        }
    },
    {
        "name": "screen_process",
        "description": (
            "Captures and analyzes the screen or webcam image. "
            "MUST be called when user asks what is on screen, what you see, "
            "analyze my screen, look at camera, etc. "
            "You have NO visual ability without this tool. "
            "After calling this tool, stay SILENT -- the vision module speaks directly."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "angle": {"type": "STRING", "description": "'screen' to capture display, 'camera' for webcam. Default: 'screen'"},
                "text":  {"type": "STRING", "description": "The question or instruction about the captured image"}
            },
            "required": ["text"]
        }
    },
    {
        "name": "computer_settings",
        "description": (
            "Controls the computer: volume (0-100), brightness (10-100), Windows settings, "
            "opening password/sign-in options, window management, keyboard shortcuts, "
            "typing text on screen, closing apps, fullscreen, dark mode, WiFi, restart, shutdown, "
            "scrolling, tab management, zoom, screenshots, lock screen, refresh/reload page. "
            "When user asks to increase/decrease/set brightness: use action='set_brightness' with value=10..100. "
            "When user asks to change Windows password: use action='change_password'."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "set_volume | set_brightness | change_password | lock_screen | screenshot | mute | open_settings | ..."},
                "description": {"type": "STRING", "description": "Natural language description of what to do"},
                "value":       {"type": "STRING", "description": "Value: volume (0-100), brightness percentage (10-100), text to type, etc."}
            },
            "required": []
        }
    },
    {
        "name": "browser_control",
        "description": (
            "Controls the web browser. Use for: opening websites, searching the web, "
            "clicking elements, filling forms, scrolling, playing content on streaming sites, "
            "and any general web-based automation task. "
            "For streaming content (Sony LIV, Netflix, Hotstar, Prime, Netmirror, JioCinema, Zee5, YouTube): "
            "use action='stream_play' with site and query."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "go_to | search | click | type | scroll | fill_form | smart_click | smart_type | get_text | press | close | stream_play | wait_for_element | get_title"},
                "url":         {"type": "STRING", "description": "URL for go_to action"},
                "query":       {"type": "STRING", "description": "Search query or content name (for search and stream_play)"},
                "site":        {"type": "STRING", "description": "Streaming site for stream_play: sony_liv | netflix | hotstar | prime | netmirror | jiocinema | zee5 | youtube"},
                "selector":    {"type": "STRING", "description": "CSS selector for click/type/wait_for_element"},
                "text":        {"type": "STRING", "description": "Text to click, type, or wait for"},
                "description": {"type": "STRING", "description": "Element description for smart_click/smart_type"},
                "direction":   {"type": "STRING", "description": "up or down for scroll"},
                "key":         {"type": "STRING", "description": "Key name for press action"},
                "timeout":     {"type": "INTEGER", "description": "Timeout in seconds for wait_for_element (default: 30)"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "file_controller",
        "description": "Manages files and folders: list, create, delete, move, copy, rename, read, write, find, disk usage.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "list | create_file | create_folder | delete | move | copy | rename | read | write | find | largest | disk_usage | organize_desktop | info"},
                "path":        {"type": "STRING", "description": "File/folder path or shortcut: desktop, downloads, documents, home"},
                "destination": {"type": "STRING", "description": "Destination path for move/copy"},
                "new_name":    {"type": "STRING", "description": "New name for rename"},
                "content":     {"type": "STRING", "description": "Content for create_file/write"},
                "name":        {"type": "STRING", "description": "File name to search for"},
                "extension":   {"type": "STRING", "description": "File extension to search (e.g. .pdf)"},
                "count":       {"type": "INTEGER", "description": "Number of results for largest"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "desktop_control",
        "description": "Controls the desktop: wallpaper, organize, clean, list, stats.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "wallpaper | wallpaper_url | organize | clean | list | stats | task"},
                "path":   {"type": "STRING", "description": "Image path for wallpaper"},
                "url":    {"type": "STRING", "description": "Image URL for wallpaper_url"},
                "mode":   {"type": "STRING", "description": "by_type or by_date for organize"},
                "task":   {"type": "STRING", "description": "Natural language desktop task"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "code_helper",
        "description": "Writes, edits, explains, runs, or builds code files.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "write | edit | explain | run | build | auto (default: auto)"},
                "description": {"type": "STRING", "description": "What the code should do or what change to make"},
                "language":    {"type": "STRING", "description": "Programming language (default: python)"},
                "output_path": {"type": "STRING", "description": "Where to save the file"},
                "file_path":   {"type": "STRING", "description": "Path to existing file for edit/explain/run/build"},
                "code":        {"type": "STRING", "description": "Raw code string for explain"},
                "args":        {"type": "STRING", "description": "CLI arguments for run/build"},
                "timeout":     {"type": "INTEGER", "description": "Execution timeout in seconds (default: 30)"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "dev_agent",
        "description": "Builds complete multi-file projects from scratch: plans, writes files, installs deps, opens VSCode, runs and fixes errors.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "description":  {"type": "STRING", "description": "What the project should do"},
                "language":     {"type": "STRING", "description": "Programming language (default: python)"},
                "project_name": {"type": "STRING", "description": "Optional project folder name"},
                "timeout":      {"type": "INTEGER", "description": "Run timeout in seconds (default: 30)"},
            },
            "required": ["description"]
        }
    },
    {
        "name": "agent_task",
        "description": (
            "Executes complex multi-step tasks requiring multiple different tools. "
            "Examples: 'research X and save to file', 'find and organize files'. "
            "DO NOT use for single commands. NEVER use for Steam/Epic -- use game_updater."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "goal":     {"type": "STRING", "description": "Complete description of what to accomplish"},
                "priority": {"type": "STRING", "description": "low | normal | high (default: normal)"}
            },
            "required": ["goal"]
        }
    },
    {
        "name": "computer_control",
        "description": "Direct computer control: type, click, hotkeys, scroll, move mouse, screenshots, find elements on screen.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "type | smart_type | click | double_click | right_click | hotkey | press | scroll | move | copy | paste | screenshot | wait | clear_field | focus_window | screen_find | screen_click | random_data | user_data"},
                "text":        {"type": "STRING", "description": "Text to type or paste"},
                "x":           {"type": "INTEGER", "description": "X coordinate"},
                "y":           {"type": "INTEGER", "description": "Y coordinate"},
                "keys":        {"type": "STRING", "description": "Key combination e.g. 'ctrl+c'"},
                "key":         {"type": "STRING", "description": "Single key e.g. 'enter'"},
                "direction":   {"type": "STRING", "description": "up | down | left | right"},
                "amount":      {"type": "INTEGER", "description": "Scroll amount (default: 3)"},
                "seconds":     {"type": "NUMBER",  "description": "Seconds to wait"},
                "title":       {"type": "STRING",  "description": "Window title for focus_window"},
                "description": {"type": "STRING",  "description": "Element description for screen_find/screen_click"},
                "type":        {"type": "STRING",  "description": "Data type for random_data"},
                "field":       {"type": "STRING",  "description": "Field for user_data: name|email|city"},
                "clear_first": {"type": "BOOLEAN", "description": "Clear field before typing (default: true)"},
                "path":        {"type": "STRING",  "description": "Save path for screenshot"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "game_updater",
        "description": (
            "THE ONLY tool for ANY Steam or Epic Games request. "
            "Use for: installing, downloading, updating games, listing installed games, "
            "checking download status, scheduling updates. "
            "ALWAYS call directly for any Steam/Epic/game request. "
            "NEVER use agent_task, browser_control, or web_search for Steam/Epic."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":    {"type": "STRING",  "description": "update | install | list | download_status | schedule | cancel_schedule | schedule_status (default: update)"},
                "platform":  {"type": "STRING",  "description": "steam | epic | both (default: both)"},
                "game_name": {"type": "STRING",  "description": "Game name (partial match supported)"},
                "app_id":    {"type": "STRING",  "description": "Steam AppID for install (optional)"},
                "hour":      {"type": "INTEGER", "description": "Hour for scheduled update 0-23 (default: 3)"},
                "minute":    {"type": "INTEGER", "description": "Minute for scheduled update 0-59 (default: 0)"},
                "shutdown_when_done": {"type": "BOOLEAN", "description": "Shut down PC when download finishes"},
            },
            "required": []
        }
    },
    {
        "name": "flight_finder",
        "description": "Searches Google Flights and speaks the best options.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "origin":      {"type": "STRING",  "description": "Departure city or airport code"},
                "destination": {"type": "STRING",  "description": "Arrival city or airport code"},
                "date":        {"type": "STRING",  "description": "Departure date (any format)"},
                "return_date": {"type": "STRING",  "description": "Return date for round trips"},
                "passengers":  {"type": "INTEGER", "description": "Number of passengers (default: 1)"},
                "cabin":       {"type": "STRING",  "description": "economy | premium | business | first"},
                "save":        {"type": "BOOLEAN", "description": "Save results to Notepad"},
            },
            "required": ["origin", "destination", "date"]
        }
    },
    {
    "name": "file_processor",
    "description": (
        "Processes any file that the user has uploaded or dropped onto the interface. "
        "Use this when the user refers to an uploaded file and wants an action on it. "
        "Supports: images (describe/ocr/resize/compress/convert), "
        "PDFs (summarize/extract_text/to_word), "
        "Word docs & text files (summarize/fix/reformat/translate), "
        "CSV/Excel (analyze/stats/filter/sort/convert), "
        "JSON/XML (validate/format/analyze), "
        "code files (explain/review/fix/optimize/run/document/test), "
        "audio (transcribe/trim/convert/info), "
        "video (trim/extract_audio/extract_frame/compress/transcribe/info), "
        "archives (list/extract), "
        "presentations (summarize/extract_text). "
        "ALWAYS call this tool when a file has been uploaded and the user gives a command about it. "
        "If the user's command is ambiguous, pick the most logical action for that file type."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "file_path": {
                "type": "STRING",
                "description": "Full path to the uploaded file. Leave empty to use the currently uploaded file."
            },
            "action": {
                "type": "STRING",
                "description": (
                    "What to do with the file. Examples by type:\n"
                    "image: describe | ocr | resize | compress | convert | info\n"
                    "pdf: summarize | extract_text | to_word | info\n"
                    "docx/txt: summarize | fix | reformat | translate_hint | word_count | to_bullet\n"
                    "csv/excel: analyze | stats | filter | sort | convert | info\n"
                    "json: validate | format | analyze | to_csv\n"
                    "code: explain | review | fix | optimize | run | document | test\n"
                    "audio: transcribe | trim | convert | info\n"
                    "video: trim | extract_audio | extract_frame | compress | transcribe | info | convert\n"
                    "archive: list | extract\n"
                    "pptx: summarize | extract_text | analyze"
                )
            },
            "instruction": {
                "type": "STRING",
                "description": "Free-form instruction if action doesn't cover it. E.g. 'translate this to Turkish', 'find all email addresses'"
            },
            "format": {
                "type": "STRING",
                "description": "Target format for conversion. E.g. 'mp3', 'pdf', 'csv', 'png'"
            },
            "width":     {"type": "INTEGER", "description": "Target width for image resize"},
            "height":    {"type": "INTEGER", "description": "Target height for image resize"},
            "scale":     {"type": "NUMBER",  "description": "Scale factor for image resize (e.g. 0.5)"},
            "quality":   {"type": "INTEGER", "description": "Quality 1-100 for image/video compress"},
            "start":     {"type": "STRING",  "description": "Start time for trim: seconds or HH:MM:SS"},
            "end":       {"type": "STRING",  "description": "End time for trim: seconds or HH:MM:SS"},
            "timestamp": {"type": "STRING",  "description": "Timestamp for video frame extraction HH:MM:SS"},
            "column":    {"type": "STRING",  "description": "Column name for CSV filter/sort"},
            "value":     {"type": "STRING",  "description": "Filter value for CSV filter"},
            "condition": {"type": "STRING",  "description": "Filter condition: equals|contains|gt|lt"},
            "ascending": {"type": "BOOLEAN", "description": "Sort order for CSV sort (default: true)"},
            "save":      {"type": "BOOLEAN", "description": "Save result to file (default: true)"},
            "destination": {"type": "STRING", "description": "Output folder for archive extract"},
        },
        "required": []
    }
},
    {
    "name": "shutdown_jarvis",
    "description": (
        "Shuts down the assistant completely. "
        "Call this when the user expresses intent to end the conversation, "
        "close the assistant, say goodbye, or stop Jarvis. "
        "The user can say this in ANY language."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {},
    }
    },
    {
        "name": "save_memory",
        "description": (
            "Save an important personal fact about the user to long-term memory. "
            "Call this silently whenever the user reveals something worth remembering: "
            "name, age, city, job, preferences, hobbies, relationships, projects, or future plans. "
            "Do NOT call for: weather, reminders, searches, or one-time commands. "
            "Do NOT announce that you are saving -- just call it silently. "
            "Values must be in English regardless of the conversation language."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "category": {
                    "type": "STRING",
                    "description": (
                        "identity -- name, age, birthday, city, job, language, nationality | "
                        "preferences -- favorite food/color/music/film/game/sport, hobbies | "
                        "projects -- active projects, goals, things being built | "
                        "relationships -- friends, family, partner, colleagues | "
                        "wishes -- future plans, things to buy, travel dreams | "
                        "notes -- habits, schedule, anything else worth remembering"
                    )
                },
                "key":   {"type": "STRING", "description": "Short snake_case key (e.g. name, favorite_food, sister_name)"},
                "value": {"type": "STRING", "description": "Concise value in English (e.g. Ansh, pizza, older sister)"},
            },
            "required": ["category", "key", "value"]
        }
    },
    {
        "name": "recall_memory",
        "description": (
            "Look up saved facts, preferences, identity details, or notes from permanent long-term memory. "
            "Call this whenever the user asks what you know about them, their preferences, projects, or saved facts."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query":    {"type": "STRING", "description": "Keyword or topic to search (e.g. 'theme', 'birthday', 'food', 'project')"},
                "category": {"type": "STRING", "description": "Optional category filter: identity | preferences | projects | relationships | wishes | notes"}
            }
        }
    },
    {
        "name": "search_conversation_history",
        "description": (
            "Search past conversation history across all previous sessions stored in SQLite memory. "
            "Call this whenever the user asks 'What did we talk about earlier?', 'Did I mention X yesterday?', or asks about past discussions."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {"type": "STRING", "description": "Topic, keyword, or sentence to search in past conversations"},
                "limit": {"type": "INTEGER", "description": "Number of past turns to return (default 10)"}
            }
        }
    },
    {
        "name": "git_controller",
        "description": (
            "Controls Git version control for code repositories. "
            "Use for: checking repo status, committing and pushing changes, pulling latest code, "
            "viewing recent commit logs, and inspecting branches."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":    {"type": "STRING", "description": "status | commit_and_push | pull | log | branch"},
                "repo_path": {"type": "STRING", "description": "Optional repository directory path"},
                "message":   {"type": "STRING", "description": "Commit message for commit_and_push"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "terminal_command",
        "description": (
            "Executes arbitrary developer CLI commands in the system terminal (e.g. npm run dev, pytest, python script.py, flutter build). "
            "Returns the command output or error code."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "command": {"type": "STRING",  "description": "The exact CLI command to run"},
                "cwd":     {"type": "STRING",  "description": "Optional working directory"},
                "timeout": {"type": "INTEGER", "description": "Timeout in seconds (default: 30)"}
            },
            "required": ["command"]
        }
    },
    {
        "name": "system_radar",
        "description": (
            "Live radar and system tracking: Indian Railways live train running status & PNR check, "
            "system RAM health check and memory optimizer, and breaking live news headlines."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":   {"type": "STRING", "description": "train_status | system_health | news"},
                "query":    {"type": "STRING", "description": "Train number or 10-digit PNR for train_status"},
                "category": {"type": "STRING", "description": "News category: tech | world | india | cricket | business (for news action)"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "smart_home",
        "description": (
            "Controls smart home IoT devices (lights, lamps, fans, AC/climate). "
            "Supports: turn_on, turn_off, set_brightness, set_color, set_temperature, status."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "device_name": {"type": "STRING", "description": "Name of device (e.g. bedroom_light, desk_lamp, main_fan, ac)"},
                "action":      {"type": "STRING", "description": "turn_on | turn_off | set_brightness | set_color | set_temperature | status"},
                "value":       {"type": "STRING", "description": "Value: brightness % (0-100), color name, or temperature in °C"}
            },
            "required": ["device_name", "action"]
        }
    },
    {
        "name": "security_protocols",
        "description": (
            "Executes emergency security lockdown protocols for the workstation: "
            "lock (instant workstation lock), cloak (minimize all windows + mute audio + clear clipboard), "
            "or panic (terminate non-essential apps + mute audio + clear clipboard + lock screen)."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "level": {"type": "STRING", "description": "lock | cloak | panic"}
            },
            "required": ["level"]
        }
    },
    {
        "name": "stream_content",
        "description": (
            "Universal free media streamer for movies, anime (Naruto, One Piece, etc.), "
            "daily serials (Taarak Mehta, CID, Anupamaa), cartoons, or web series. "
            "Uses user's saved source preference if previously set."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "title":      {"type": "STRING", "description": "Title of the movie, anime, serial episode, or show to play"},
                "media_type": {"type": "STRING", "description": "auto | anime | serial | movie | cartoon | series (default: auto)"},
                "custom_url": {"type": "STRING", "description": "Optional direct streaming URL override"}
            },
            "required": ["title"]
        }
    },
    {
        "name": "save_media_source_preference",
        "description": (
            "Permanently remembers user's preferred website or platform for a specific show, anime, or category "
            "(e.g. 'Taarak Mehta SonyLIV se dikhana' or 'Anime hamesha site X se play karna')."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "keyword_or_title": {"type": "STRING", "description": "Show title or category keyword (e.g. taarak_mehta, anime, movies)"},
                "url_or_platform":  {"type": "STRING", "description": "Platform name or URL (e.g. sonyliv, hianime, https://...)"}
            },
            "required": ["keyword_or_title", "url_or_platform"]
        }
    },
    {
        "name": "search_and_show_products",
        "description": (
            "Contextual e-commerce shopping discovery across Amazon India, Flipkart, or Myntra. "
            "Automatically incorporates user's saved size and brand preferences from SQLite memory."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "category_or_item": {"type": "STRING", "description": "Item or product description (e.g. 'black formal shirt', 'running shoes')"},
                "budget":           {"type": "STRING", "description": "Budget limit or price range (e.g. '2000', '1500-3000')"},
                "size":             {"type": "STRING", "description": "Size (e.g. 'M', 'L', 'XL', '9 UK')"},
                "color_or_style":   {"type": "STRING", "description": "Color or style description (e.g. 'navy blue slim fit')"},
                "platform":         {"type": "STRING", "description": "amazon | flipkart | myntra (default: amazon)"}
            },
            "required": ["category_or_item"]
        }
    },
    {
        "name": "proceed_to_cart_and_checkout",
        "description": (
            "Navigates to the selected product page, selects size, and adds to cart / opens checkout screen. "
            "STRICT SAFETY: Always stops before payment submission for explicit user confirmation."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "product_url": {"type": "STRING", "description": "Direct product URL on Amazon/Flipkart/Myntra"},
                "size":        {"type": "STRING", "description": "Size to select before adding to cart"}
            },
            "required": []
        }
    },
    {
        "name": "save_shopping_preference",
        "description": (
            "Saves user measurements and shopping preferences into permanent memory "
            "(e.g. shirt_size: 'M', shoe_size: '9', preferred_brand: 'Zara', budget_range: '2000')."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "key":   {"type": "STRING", "description": "shirt_size | shoe_size | pant_size | preferred_brand | budget_range"},
                "value": {"type": "STRING", "description": "Preference value (e.g. 'M', '9 UK', 'Levis', '1500-3000')"}
            },
            "required": ["key", "value"]
        }
    },
    {
        "name": "bluetooth_control",
        "description": (
            "Autonomous Bluetooth controller on Windows: disconnect or connect specific Bluetooth devices "
            "(e.g. 'KH-Q8', 'realme Buds', 'Galaxy S24', 'airpods', 'headphones'), list paired and connected devices, "
            "or turn Bluetooth radio on/off/toggle."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "disconnect | connect | list | toggle_radio | turn_on | turn_off | settings"
                },
                "device_name": {
                    "type": "STRING",
                    "description": "Name or keyword of the Bluetooth device (e.g. 'KH-Q8', 'kh q 8', 'realme', 'boat', 'galaxy')"
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "deep_research",
        "description": (
            "Deep multi-source web research engine. Use ONLY when the user explicitly asks for research, "
            "or asks for dynamic live web data like today's live sports scores/standings (IPL, cricket), "
            "today's breaking news, recent product benchmarks, or upcoming unreleased movie/game release dates. "
            "DO NOT call this for basic facts, general knowledge, or definitions that you already know -- answer those directly."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query":  {"type": "STRING", "description": "What to research (e.g. 'IPL 2025 points table', 'GTA 6 PC release date')"},
                "domain": {"type": "STRING", "description": "sports | cricket | ipl | football | movies | games | tech | ai | news | general (default: general)"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "mobile_bridge",
        "description": (
            "Android ADB wireless bridge. Use to: connect phone over Wi-Fi, make phone calls, "
            "send SMS, or check phone battery/status. Requires ADB tools installed and phone on same Wi-Fi."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":       {"type": "STRING", "description": "connect | call | sms | status"},
                "ip_address":   {"type": "STRING", "description": "Phone IP address (for connect action)"},
                "port":         {"type": "INTEGER", "description": "ADB port (default 5555)"},
                "phone_number": {"type": "STRING", "description": "Phone number (for call/sms action)"},
                "message":      {"type": "STRING", "description": "SMS message text (for sms action)"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "live_writer",
        "description": (
            "Generate and open code or study notes files. Use when user says: "
            "'write code for X', 'generate Python for Y', 'create notes on Z', 'likhdo X ke baare mein'. "
            "Saves file to Desktop and opens it in VS Code or Notepad."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "subject":   {"type": "STRING", "description": "Subject or project name (e.g. 'Machine Learning', 'Web Scraping')"},
                "topic":     {"type": "STRING", "description": "Specific topic or task to write (e.g. 'binary search algorithm', 'neural network from scratch')"},
                "file_type": {"type": "STRING", "description": "python | javascript | html | css | markdown | notes | text | java | cpp | sql (default: python)"}
            },
            "required": ["subject", "topic"]
        }
    },
    {
        "name": "teleport_workspace",
        "description": (
            "Organize desktop windows into named layouts. Use when user says: "
            "'split screen', 'dev layout', 'maximize', 'quad layout', 'windows arrange karo'. "
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "layout": {"type": "STRING", "description": "split_dev | focus | quad | split_left | split_right (default: split_dev)"}
            },
            "required": []
        }
    },
    {
        "name": "security_vault",
        "description": "Security PIN management. Set, verify, or clear a 4-digit startup PIN.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "verify | set | clear"},
                "pin":    {"type": "STRING", "description": "4-digit PIN"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "screen_understand",
        "description": (
            "Visual Question Answering (VQA) about the current computer screen. "
            "Use when user asks: 'what is on my screen?', 'what error is showing?', 'what app is open?', "
            "'read this page', 'is bluetooth toggle on?', 'what does this button say?'. "
            "Analyzes the live screen visually and returns a factual spoken answer."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {"type": "STRING", "description": "Specific visual question or query about the screen content"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "vision_find_element",
        "description": (
            "Ground a UI element visually on screen without clicking. "
            "Returns coordinates (x, y), bounding box, confidence score, and ambiguity status."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "target":  {"type": "STRING", "description": "Name or description of UI element to locate (e.g. 'Download button', 'search box')"},
                "context": {"type": "STRING", "description": "Optional surrounding context or position (e.g. 'top right', 'inside settings dialog')"}
            },
            "required": ["target"]
        }
    },
    {
        "name": "vision_click",
        "description": (
            "Locate and safely click a UI target or sequential chain of targets on screen using visual grounding. "
            "Supports single targets ('download button') and multi-step chains ('connection -> connect -> connect' or 'connection pr click kro fir connect pr'). "
            "Automatically executes each step in sequence with screen re-capture."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "target":  {"type": "STRING", "description": "Target button/menu name or arrow-separated sequence (e.g. 'connection -> connect -> connect')"},
                "context": {"type": "STRING", "description": "Optional contextual clue (e.g. 'in the header', 'WO Mic Client window')"}
            },
            "required": ["target"]
        }
    },
    {
        "name": "vision_type",
        "description": (
            "Visually locate an input field, address bar, or search box on screen, focus it, and type text. "
            "Use for: 'search X on YouTube', 'type Y in search bar', 'enter URL Z in browser'. "
            "Automatically clears field, pastes text with Unicode support, and optionally presses Enter."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "target":      {"type": "STRING",  "description": "Visual description of input/search box (e.g. 'YouTube search bar', 'address bar')"},
                "text":        {"type": "STRING",  "description": "Text or query to type"},
                "press_enter": {"type": "BOOLEAN", "description": "Whether to press Enter after typing (default: true)"},
                "clear_first": {"type": "BOOLEAN", "description": "Whether to clear existing text first (default: true)"}
            },
            "required": ["text"]
        }
    },
    {
        "name": "vision_scroll",
        "description": (
            "Scroll on the screen or within a visually grounded container (feed, results, document). "
            "Use for: 'scroll down', 'scroll up', 'page down', 'scroll the comments'."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "direction": {"type": "STRING",  "description": "down | up (default: down)"},
                "amount":    {"type": "INTEGER", "description": "Scroll distance (default: 300)"},
                "target":    {"type": "STRING",  "description": "Optional container or area to scroll on"}
            },
            "required": []
        }
    },
    {
        "name": "vision_engine",
        "description": (
            "Unified computer vision and visual interaction engine for desktop GUI tasks. "
            "Actions: click | type | scroll | drag | inspect | locate | ocr."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":  {"type": "STRING", "description": "click | type | scroll | inspect | locate | ocr"},
                "target":  {"type": "STRING", "description": "Target UI element or container description"},
                "text":    {"type": "STRING", "description": "Text to type (for type action)"},
                "query":   {"type": "STRING", "description": "Visual question or query (for inspect action)"},
                "context": {"type": "STRING", "description": "Optional context"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "universal_ad_skipper",
        "description": (
            "Visually inspects the active screen across ANY desktop app or website (YouTube, Spotify, "
            "Hotstar, Prime, JioCinema, Zee5, Netflix, Chrome, Edge, games, BlueStacks) and clicks "
            "Skip Ad, Close Ad, 'X', No thanks, or dismiss buttons automatically. "
            "Supports continuous auto-skip sentinel mode: action='start_auto_skip'."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "skip_ad (default, single scan & skip) | start_auto_skip (continuous background watcher) | stop_auto_skip | status"
                },
                "app_or_site": {
                    "type": "STRING",
                    "description": "Optional app or website hint (e.g. 'youtube', 'spotify', 'hotstar', 'prime', 'browser')"
                },
                "duration_seconds": {
                    "type": "INTEGER",
                    "description": "Duration in seconds for auto_skip sentinel mode (default 1800)"
                }
            },
            "required": []
        }
    },
    {
        "name": "app_settings_navigator",
        "description": (
            "Opens any desktop application or browser (e.g. Chrome, VS Code, Spotify, Telegram, Discord, Steam, Settings), "
            "visually scans the window to find and click its Settings / Preferences / Gear ⚙️ icon, "
            "inspects the available settings options, and executes the user's requested configuration change or asks for details."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "app_name": {
                    "type": "STRING",
                    "description": "Name of the application (e.g. 'Chrome', 'VS Code', 'Spotify', 'Telegram', 'Discord', 'Steam')"
                },
                "setting_task": {
                    "type": "STRING",
                    "description": "The specific task or change to make in settings (e.g. 'dark mode', 'download location', 'audio settings', or leave empty to inspect and ask)"
                }
            },
            "required": ["app_name"]
        }
    },
    {
        "name": "video_editor",
        "description": (
            "Autonomous AI Video Editing Suite. Use when user wants to edit, cut, trim, compress, "
            "convert, extract audio, add background music, change speed (slow-mo/timelapse), convert to Reels/Shorts (9:16), "
            "create animated GIFs, apply filters (black & white/sepia/vintage), mute, reverse, or merge videos."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "trim | extract_audio | add_audio | merge | change_speed | aspect_ratio | compress | extract_frame | create_gif | mute | reverse | filter | info"
                },
                "video_path":   {"type": "STRING",  "description": "Path to the video file"},
                "start":        {"type": "STRING",  "description": "Start timestamp for trim/gif (e.g. '00:00:10' or '10')"},
                "end":          {"type": "STRING",  "description": "End timestamp for trim (e.g. '00:01:30' or '90')"},
                "audio_path":   {"type": "STRING",  "description": "Audio file path for add_audio/replace_audio"},
                "mix_mode":     {"type": "STRING",  "description": "'replace' audio track or 'overlay' background music"},
                "volume":       {"type": "NUMBER",  "description": "Background music volume level (0.1 to 1.0, default: 0.3)"},
                "speed":        {"type": "NUMBER",  "description": "Playback speed multiplier (e.g. 0.5 for slowmo, 2.0 for fast/timelapse)"},
                "aspect":       {"type": "STRING",  "description": "Target aspect ratio: '9:16' (Reels/Shorts/TikTok), '16:9' (YouTube), '1:1' (Instagram)"},
                "preset":       {"type": "STRING",  "description": "Compression preset: 'whatsapp' | 'discord' | 'high' | 'low'"},
                "format":       {"type": "STRING",  "description": "Audio format for extract_audio: 'mp3' | 'wav' | 'aac'"},
                "filter_name":  {"type": "STRING",  "description": "Filter effect: 'black_and_white' | 'sepia' | 'vintage' | 'brighten' | 'vignette'"},
                "timestamp":    {"type": "STRING",  "description": "Timestamp for frame snapshot (e.g. '00:00:05')"},
                "video_paths":  {"type": "ARRAY", "items": {"type": "STRING"}, "description": "List of video file paths for merge action"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "image_generator",
        "description": (
            "Autonomous Neural Image Generator & Art Studio. Generates high-definition AI images, concept art, "
            "illustrations, anime art, 3D renders, and wallpapers using FLUX.1/SDXL and displays them instantly on the screen HUD image card."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "prompt": {
                    "type": "STRING",
                    "description": "Visual description of the image to generate (e.g. 'futuristic cyberpunk city with neon lights', 'majestic golden eagle in mountains')"
                },
                "aspect_ratio": {
                    "type": "STRING",
                    "description": "Aspect ratio: '1:1' (Square), '16:9' (Landscape/Wallpaper), '9:16' (Story/Reels/Portrait)"
                },
                "style": {
                    "type": "STRING",
                    "description": "Art style: 'photorealistic' | 'cyberpunk' | 'anime' | 'cinematic' | '3d_render' | 'digital_art'"
                },
                "set_as_wallpaper": {
                    "type": "BOOLEAN",
                    "description": "Set the newly generated image as the Windows desktop wallpaper immediately"
                }
            },
            "required": ["prompt"]
        }
    },
    {
        "name": "smart_downloader",
        "description": (
            "Autonomous Smart Downloader & Media Retrieval Engine. Downloads ANY file, software, installer, "
            "video, audio, PDF, or zip from any website (YouTube, Instagram, X, Reddit, TikTok, direct link, or web pages). "
            "If the download flow is complex or requires human captcha/login, it inspects tutorials, opens the page, and guides the user in Hinglish."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "url": {
                    "type": "STRING",
                    "description": "Website URL, video link, or direct download link"
                },
                "item_name": {
                    "type": "STRING",
                    "description": "Name of the software, file, or item to download (e.g. 'Blender', 'Python 3.12 installer', 'Minecraft mod', 'song name')"
                },
                "format": {
                    "type": "STRING",
                    "description": "Media format: 'video' (MP4) | 'audio' (MP3) | 'direct'"
                },
                "action": {
                    "type": "STRING",
                    "description": "'download' | 'tutorial' | 'open_folder'"
                }
            }
        }
    },
    {
        "name": "app_installer",
        "description": (
            "Autonomous Windows Software & Application Installer. Installs, updates, or uninstalls ANY app or package "
            "(e.g. Chrome, VS Code, Discord, Spotify, Steam, VLC, Blender, Git, Node.js, Python, 7-Zip, Telegram) "
            "silently using Winget (Windows Package Manager), pip, npm, or direct installer execution."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "'install' | 'uninstall' | 'search'"
                },
                "app_name": {
                    "type": "STRING",
                    "description": "Name of the application or package (e.g. 'Google Chrome', 'VS Code', 'Discord', 'Blender', 'pip install pygame')"
                },
                "source": {
                    "type": "STRING",
                    "description": "'auto' | 'winget' | 'pip' | 'npm'"
                }
            },
            "required": ["app_name"]
        }
    },
    {
        "name": "search_conversation_history",
        "description": (
            "Searches past conversation turns, previous sessions, and chat history by keyword, topic, date "
            "('yesterday', 'kal', '25 August', 'last week'), or generic history requests "
            "('previous conversation', 'pichli baat', 'what did we talk about'). "
            "Returns accurate timestamps, dates, user messages, and INDUS responses."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": "Search keyword, topic, date, or leave empty/generic for recent history"
                }
            },
            "required": []
        }
    },
    {
        "name": "recall_memory",
        "description": (
            "Recalls saved personal facts, preferences, habits, projects, and user profile information stored in permanent long-term memory."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": "Fact keyword or query to recall (e.g. 'name', 'theme', 'size', 'birthday', 'city')"
                },
                "category": {
                    "type": "STRING",
                    "description": "Optional category: identity | preferences | habits | projects | relationships | wishes | notes"
                }
            },
            "required": []
        }
    },
]

import atexit
from memory.memory_manager import flush_memory_on_shutdown
atexit.register(flush_memory_on_shutdown)






# ---------------------------------------------------------------------------
# Tool registry dispatch helpers — used by JarvisLive._execute_tool()
# These replace the old 300-line if-elif chain.
# ---------------------------------------------------------------------------
from core.tool_registry import dispatch_with_speak as _tool_registry_dispatch_with_speak


def _registry_dispatch(tool_name: str, args: dict, player=None):
    """Dispatch a tool via the canonical registry (no speak callback)."""
    result, err = _tool_registry_dispatch_with_speak(tool_name, args, player=player)
    if err:
        return f"[Registry Error] {err}"
    return result


def _registry_dispatch_speak(tool_name: str, args: dict, player=None, speak=None):
    """Dispatch a tool via the canonical registry, passing speak callback if supported."""
    result, err = _tool_registry_dispatch_with_speak(tool_name, args, player=player, speak=speak)
    if err:
        return f"[Registry Error] {err}"
    return result


class JarvisLive:

    def __init__(self, ui: JarvisUI):
        self.ui             = ui
        self.session        = None
        self.audio_in_queue = None
        self.out_queue      = None
        self._loop          = None
        self._is_speaking   = False
        self._speaking_lock = threading.Lock()
        self.ui.on_text_command = self._on_text_command
        cancellation_manager.register_callback(self._on_cancellation_event)
        wake_word_controller.on_activate = self._on_wake_word_activate
        wake_word_controller.on_deactivate = self._on_wake_word_deactivate

    def _on_wake_word_activate(self, source: str, buffered_audio: bytes):
        """Called when wake word (e.g. 'INDUS', 'Hey INDUS') is detected."""
        print(f"[JarvisLive] Wake word activation: '{source}'")
        cancellation_manager.reset()
        self.ui.set_state("ACTIVATING")
        self.ui.write_log(f"• SYS: [WakeWord] Activated by '{source}'")
        time.sleep(0.1)
        if not self.ui.muted:
            self.ui.set_state("LISTENING")

        # Forward captured trailing audio buffer directly to Gemini Live
        if buffered_audio and self.out_queue is not None and self._loop is not None:
            try:
                self._loop.call_soon_threadsafe(
                    self.out_queue.put_nowait,
                    {"data": buffered_audio, "mime_type": f"audio/pcm;rate={SEND_SAMPLE_RATE}"}
                )
            except Exception:
                pass

    def _on_wake_word_deactivate(self, reason: str):
        """Called when inactivity timeout elapses or user says 'standby'."""
        print(f"[JarvisLive] Returning to STANDBY: {reason}")
        if not self.ui.muted:
            self.ui.set_state("STANDBY")
        self.ui.write_log(f"• SYS: [Standby] {reason}")

    def _flush_audio_playback(self):
        """Immediately drop all queued TTS audio chunks to silence playback in <10ms."""
        if self.audio_in_queue is not None:
            while not self.audio_in_queue.empty():
                try:
                    self.audio_in_queue.get_nowait()
                    self.audio_in_queue.task_done()
                except Exception:
                    break

    def _on_cancellation_event(self, reason: str):
        self._flush_audio_playback()
        self.set_speaking(False)
        self.ui.set_audio_level(0.0)

    def cancel_active_task(self, reason: str = "User voice interruption"):
        """Immediately stop running cancellable operations and silence TTS."""
        print(f"[JarvisLive] Interruption triggered: {reason}")
        cancellation_manager.request_cancellation(reason)
        self._flush_audio_playback()
        self.set_speaking(False)
        self.ui.set_audio_level(0.0)
        self.ui.set_state("CANCELLING")
        self.ui.write_log(f"SYS: [Interrupted] {reason}")
        time.sleep(0.1)
        self.ui.set_state("CANCELLED")
        time.sleep(0.15)
        if not self.ui.muted:
            self.ui.set_state("LISTENING" if wake_word_controller.is_active else "STANDBY")

    def _on_text_command(self, text: str):
        if is_stop_phrase(text):
            self.cancel_active_task(reason=f"Text command: '{text}'")
            return
        if is_standby_phrase(text):
            wake_word_controller.deactivate(reason=f"Text command: '{text}'")
            return

        # Activate on user text input
        wake_word_controller.activate(source="UI Text Input")
        cancellation_manager.reset()

        if not self._loop or not self.session:
            print("[JarvisLive] [WARN] Session not connected yet for text command.")
            return

        # Save user text immediately to DB so it appears in context on reconnect
        try:
            from memory.db_engine import db_save_conversation
            db_save_conversation(text, "", intent="text_input")
        except Exception:
            pass

        async def _send():
            try:
                await self.session.send_client_content(
                    turns=[{"parts": [{"text": text}]}],
                    turn_complete=True
                )
            except Exception as e:
                print(f"[JarvisLive] [ERR] send_client_content error: {e}")

        asyncio.run_coroutine_threadsafe(_send(), self._loop)


    def set_speaking(self, value: bool):
        with self._speaking_lock:
            self._is_speaking = value
        if value:
            self.ui.set_state("SPEAKING")
            try:
                self.ui.avatar.start_speaking()
            except Exception:
                pass
        elif not self.ui.muted:
            self.ui.set_state("LISTENING")
            try:
                self.ui.avatar.stop_speaking()
            except Exception:
                pass

    def speak(self, text: str):
        if not self._loop or not self.session:
            return

        async def _send():
            try:
                await self.session.send_client_content(
                    turns=[{"parts": [{"text": text}]}],
                    turn_complete=True
                )
            except Exception as e:
                print(f"[JarvisLive] [ERR] speak send error: {e}")

        asyncio.run_coroutine_threadsafe(_send(), self._loop)


    def speak_error(self, tool_name: str, error: str):
        short = str(error)[:120]
        self.ui.write_log(f"ERR: {tool_name} -- {short}")
        self.speak(f"Ansh, {tool_name} mein ek error aayi. {short}")

    def _build_config(self) -> types.LiveConnectConfig:
        from datetime import datetime

        memory     = load_memory()
        mem_str    = format_memory_for_prompt(memory)
        sys_prompt = _load_system_prompt()

        now      = datetime.now()
        time_str = now.strftime("%A, %B %d, %Y -- %I:%M %p")
        time_ctx = (
            f"[CURRENT DATE & TIME]\n"
            f"Right now it is: {time_str}\n"
            f"Use this to calculate exact times for reminders.\n\n"
        )

        parts = [time_ctx]
        if mem_str:
            # Cap memory context at 6000 chars to prevent Gemini system prompt token overflow
            # after many sessions. Trim from the middle, keeping start (identity facts)
            # and end (recent preferences) which are most relevant.
            MAX_MEM_CHARS = 6000
            if len(mem_str) > MAX_MEM_CHARS:
                half = MAX_MEM_CHARS // 2
                mem_str = (
                    mem_str[:half]
                    + "\n\n[...older memory trimmed to fit context window...]\n\n"
                    + mem_str[-half:]
                )
            parts.append(mem_str)
        parts.append(sys_prompt)

        return types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            output_audio_transcription={},
            input_audio_transcription={},
            system_instruction="\n".join(parts),
            tools=[{"function_declarations": TOOL_DECLARATIONS}],
            session_resumption=types.SessionResumptionConfig(),
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name="Aoede"
                    )
                )
            ),
        )

    async def _execute_tool(self, fc) -> types.FunctionResponse:
        name = fc.name
        args = dict(fc.args or {})

        # -- Cancellation check -----------------------------------------
        if cancellation_manager.is_cancelled():
            print(f"[JARVIS] Tool '{name}' skipped (active cancellation).")
            event_bus.publish(E.TOOL_CANCELLED, source="execute_tool",
                              data={"tool": name, "reason": "pre-existing cancellation"})
            if not self.ui.muted:
                self.ui.set_state("LISTENING")
            return types.FunctionResponse(
                id=fc.id, name=name,
                response={"result": "Operation cancelled by user.", "cancelled": True}
            )

        # -- Announce tool request --------------------------------------
        event_bus.publish(E.TOOL_REQUESTED, source="gemini_live",
                          data={"tool": name, "args_keys": list(args.keys())})

        # -- SECURITY GATE -- every Gemini Live call must pass this (FAIL-CLOSED) --
        if name not in ("save_memory", "shutdown_jarvis"):
            try:
                sec = security_engine(tool_name=name, parameters=args, user_context={"ui": self.ui})
                event_bus.publish(E.SECURITY_CHECK, source="execute_tool",
                                  data={"tool": name, "risk": sec.risk_level,
                                        "allowed": sec.allowed})

                if sec.requires_confirmation:
                    msg = (
                        f"[Confirmation Required] Action '{name}' targeting '{sec.target}' "
                        f"has risk level '{sec.risk_level}'. {sec.reason} "
                        f"Use confirmation_token='{sec.confirmation_token}' to authorize."
                    )
                    print(f"[JARVIS] [Security] {msg}")
                    self.ui.write_log(f"• SEC-ALERT: {msg}")
                    try:
                        if hasattr(self.ui, "show_security_confirmation_card"):
                            self.ui.show_security_confirmation_card(action=name, target=sec.target, risk=sec.risk_level, token=sec.confirmation_token)
                    except Exception:
                        pass
                    if not self.ui.muted:
                        self.ui.set_state("LISTENING")
                    cancellation_manager.clear_active_task()
                    return types.FunctionResponse(
                        id=fc.id, name=name,
                        response={
                            "result": msg,
                            "requires_confirmation": True,
                            "confirmation_token": sec.confirmation_token,
                            "risk": sec.risk_level,
                            "target": sec.target
                        }
                    )

                if not sec.allowed:
                    msg = f"[Security Deny] Action '{name}' blocked: {sec.reason}"
                    print(f"[JARVIS] {msg}")
                    self.ui.write_log(f"• SEC: {msg}")
                    if not self.ui.muted:
                        self.ui.set_state("LISTENING")
                    cancellation_manager.clear_active_task()
                    return types.FunctionResponse(
                        id=fc.id, name=name,
                        response={"result": msg, "blocked": True, "risk": sec.risk_level}
                    )
            except Exception as sec_err:
                # ── FAIL-CLOSED INVARIANT: NEVER ALLOW ON EXCEPTION ───────────
                audit_logger.log_security_alert(
                    alert_type="SECURITY_GATE_EXCEPTION_DENY",
                    tool=name,
                    details=f"Gate exception: {sec_err}",
                    severity="DESTRUCTIVE"
                )
                msg = f"[Security Deny] Action '{name}' blocked: Security gate error (Fail-Closed protection)."
                print(f"[JARVIS] {msg} ({sec_err})")
                self.ui.write_log(f"• SEC-FAIL-CLOSED: {msg}")
                if not self.ui.muted:
                    self.ui.set_state("LISTENING")
                cancellation_manager.clear_active_task()
                return types.FunctionResponse(
                    id=fc.id, name=name,
                    response={"result": msg, "blocked": True, "risk": "DESTRUCTIVE"}
                )

        cancellation_manager.set_active_task(name)
        print(f"[JARVIS] [Tool] {name}  {args}")
        self.ui.set_state("EXECUTING")

        if name == "save_memory":
            category = args.get("category", "notes")
            key      = args.get("key", "")
            value    = args.get("value", "")
            if key and value:
                update_memory({category: {key: {"value": value}}})
                print(f"[Memory] save_memory: {category}/{key} = {value}")
            if not self.ui.muted:
                self.ui.set_state("LISTENING")
            return types.FunctionResponse(
                id=fc.id, name=name,
                response={"result": "ok", "silent": True}
            )


        loop   = asyncio.get_event_loop()
        result = "Done."
        wake_word_controller.touch()

        # Publish TOOL_STARTED -- visible in HUD event log
        event_bus.publish(E.TOOL_STARTED, source="execute_tool",
                          data={"tool": name, "args_keys": list(args.keys())})

        try:
            # ─── SPECIAL-CASE TOOLS (require async/threading/UI hooks) ──────────────

            # save_memory: inline update — no round-trip to executor
            if name == "save_memory":
                category = args.get("category", "notes")
                key      = args.get("key", "")
                value    = args.get("value", "")
                if key and value:
                    update_memory({category: {key: {"value": value}}})
                    print(f"[Memory] save_memory: {category}/{key} = {value}")
                if not self.ui.muted:
                    self.ui.set_state("LISTENING")
                return types.FunctionResponse(
                    id=fc.id, name=name,
                    response={"result": "ok", "silent": True}
                )

            # shutdown_jarvis: async shutdown — must run outside executor
            elif name == "shutdown_jarvis":
                self.ui.write_log("SYS: Shutdown requested.")
                self.speak("Goodbye, Ansh. Take care!")
                def _shutdown():
                    import time, os
                    time.sleep(1)
                    os._exit(0)
                threading.Thread(target=_shutdown, daemon=True).start()
                result = "Shutting down."

            # recall_memory / search_conversation_history: sync, no executor needed
            elif name == "recall_memory":
                from memory.memory_manager import recall_memory as _recall
                result = _recall(
                    query=args.get("query", ""),
                    category=args.get("category", "")
                ) or "No memory records found."

            elif name == "search_conversation_history":
                from memory.memory_manager import search_conversation_history as _sch
                lim = int(args.get("limit", 10)) if args.get("limit") else 10
                result = _sch(
                    query=args.get("query", ""),
                    limit=lim
                ) or "No conversation history found."

            # agent_task: delegates to the closed-loop agent
            elif name == "agent_task":
                from agent.agent_loop import closed_loop_agent
                r = await loop.run_in_executor(
                    None,
                    lambda: closed_loop_agent.execute_goal(
                        goal=args.get("goal", ""), player_ui=self.ui, speak=self.speak
                    )
                )
                result = r or "Task completed."

            # screen_process: MUST run in a thread, not await (spawns its own async loop)
            elif name == "screen_process":
                threading.Thread(
                    target=screen_process,
                    kwargs={"parameters": args, "response": None,
                            "player": self.ui, "session_memory": None},
                    daemon=True
                ).start()
                result = "Vision module activated. Stay completely silent — vision module will speak directly."

            # web_search: show info card before and after
            elif name == "web_search":
                _ws_query = args.get("query", "") or ", ".join(args.get("items", []))
                try:
                    self.ui.show_info_card(query=_ws_query)
                except Exception:
                    pass
                _ui = self.ui
                r = await loop.run_in_executor(
                    None, lambda: _registry_dispatch(name, args, player=_ui)
                )
                result = r or "Done."
                try:
                    self.ui.update_info_card(result=result)
                except Exception:
                    pass

            # deep_research: show info card before and after
            elif name == "deep_research":
                _dr_query = args.get("query", "")
                try:
                    self.ui.show_info_card(query=_dr_query)
                except Exception:
                    pass
                _ui = self.ui
                r = await loop.run_in_executor(
                    None, lambda: _registry_dispatch(name, args, player=_ui)
                )
                result = r or "Research complete."
                try:
                    self.ui.update_info_card(result=result)
                except Exception:
                    pass

            # file_processor: inject current_file from UI if path not provided
            elif name == "file_processor":
                if not args.get("file_path") and self.ui.current_file:
                    args["file_path"] = self.ui.current_file
                _ui, _spk = self.ui, self.speak
                r = await loop.run_in_executor(
                    None, lambda: _registry_dispatch_speak(name, args, player=_ui, speak=_spk)
                )
                result = r or "Done."

            # ─── ALL OTHER TOOLS ────────────────────────────────────────────────────
            # Route through the canonical tool registry (single path for voice + text)
            else:
                _ui, _spk = self.ui, self.speak
                r = await loop.run_in_executor(
                    None, lambda: _registry_dispatch_speak(name, args, player=_ui, speak=_spk)
                )
                result = r or "Done."



        except Exception as e:
            result = f"Tool '{name}' failed: {e}"
            traceback.print_exc()
            event_bus.publish(E.TOOL_FAILED, source="execute_tool",
                              data={"tool": name, "error": str(e)[:200]})
            if not cancellation_manager.is_cancelled():
                self.speak_error(name, e)
        finally:
            cancellation_manager.clear_active_task()
            wake_word_controller.touch()
            if not self.ui.muted and self.ui.state not in ("CANCELLING", "CANCELLED"):
                self.ui.set_state("LISTENING")

        if cancellation_manager.is_cancelled():
            print(f"[JARVIS] Tool '{name}' result discarded (cancelled by user).")
            event_bus.publish(E.TOOL_CANCELLED, source="execute_tool",
                              data={"tool": name})
            return types.FunctionResponse(
                id=fc.id, name=name,
                response={"result": "Operation was cancelled by user.", "cancelled": True}
            )

        # Normalize raw string/dict result to ToolResult contract
        tool_result = normalize_result(result, tool_name=name)
        result_str  = tool_result.to_str()

        event_bus.publish(E.TOOL_COMPLETED, source="execute_tool",
                          data={"tool": name, "success": tool_result.success,
                                "result_preview": result_str[:80]})

        print(f"[JARVIS] [Result] {name} -> {result_str[:80]}")

        return types.FunctionResponse(
            id=fc.id, name=name,
            response={"result": result_str, "success": tool_result.success}
        )

    async def _send_realtime(self):
        while True:
            msg = await self.out_queue.get()
            try:
                await self.session.send_realtime_input(media=msg)
            except Exception as e:
                print(f"[INDUS] [WARN] send_realtime: {e}")
            finally:
                self.out_queue.task_done()

    async def _inactivity_monitor(self):
        """Periodically checks inactivity timeout to return to STANDBY when idle."""
        while True:
            await asyncio.sleep(1.0)
            with self._speaking_lock:
                speaking = self._is_speaking
            if not speaking and not self.ui.muted:
                wake_word_controller.check_inactivity()

    async def _listen_audio(self):
        print("[INDUS] [MIC] Mic started")
        loop = asyncio.get_event_loop()
        from actions.audio_service import create_input_stream

        def pcm_callback(pcm_bytes: bytes, rms: float):
            with self._speaking_lock:
                jarvis_speaking = self._is_speaking
            if not jarvis_speaking and not self.ui.muted:
                # Feed to wake word controller
                should_forward = wake_word_controller.feed_audio(pcm_bytes, rms)

                if should_forward:
                    if rms > 20.0:
                        level = min(1.0, (rms / 2200.0))
                        self.ui.set_audio_level(level)
                    try:
                        if self.out_queue.full():
                            try:
                                self.out_queue.get_nowait()
                                self.out_queue.task_done()
                            except Exception:
                                pass
                        loop.call_soon_threadsafe(
                            self.out_queue.put_nowait,
                            {"data": pcm_bytes, "mime_type": f"audio/pcm;rate={SEND_SAMPLE_RATE}"}
                        )
                    except Exception:
                        pass
                else:
                    # In STANDBY mode: minimal idle pulse indicator when speech detected
                    if rms > 40.0:
                        self.ui.set_audio_level(0.12)

        try:
            stream, actual_dev, actual_sr = create_input_stream(
                pcm_16k_callback=pcm_callback,
                blocksize=CHUNK_SIZE
            )
            with stream:
                print(f"[INDUS] [MIC] Mic stream open (Device [{actual_dev}], Native: {actual_sr}Hz -> {SEND_SAMPLE_RATE}Hz)")
                self.ui.write_log(f"• SYS: Mic online (Dev [{actual_dev}], {actual_sr}Hz)")
                while True:
                    await asyncio.sleep(0.1)
        except Exception as e:
            print(f"[INDUS] [ERR] Mic error: {e}")
            self.ui.write_log(f"• SYS: Microphone error: {e}")
            raise


    async def _receive_audio(self):
        print("[JARVIS] [RECV] Recv started")
        out_buf, in_buf = [], []

        try:
            while True:
                async for response in self.session.receive():

                    if response.data:
                        self.audio_in_queue.put_nowait(response.data)

                    if response.server_content:
                        sc = response.server_content

                        if sc.output_transcription and sc.output_transcription.text:
                            self.set_speaking(True)
                            raw_txt = sc.output_transcription.text
                            txt = re.sub(r"<ctrl\d+>", "", raw_txt)
                            if txt:
                                out_buf.append(txt)
                                # ── Viseme lip sync: feed text → phoneme timeline ──
                                try:
                                    self.ui.avatar.feed_speech_text(txt)
                                except Exception:
                                    pass
                                # ── Emoji → emotion face change ──────────────────
                                try:
                                    self.ui.avatar.detect_and_set_emotion(txt)
                                except Exception:
                                    pass

                        if sc.input_transcription and sc.input_transcription.text:
                            raw_txt = sc.input_transcription.text
                            txt = re.sub(r"<ctrl\d+>", "", raw_txt)
                            if txt:
                                in_buf.append(txt)
                                full_in_check = "".join(in_buf).strip()
                                # Real-time voice interruption check (deterministic, sub-10ms)
                                if is_stop_phrase(txt) or is_stop_phrase(full_in_check):
                                    print(f"[JarvisLive] Voice Interruption Detected: '{full_in_check}'")
                                    self.cancel_active_task(reason=f"Spoken: '{full_in_check}'")
                                    continue

                                # Real-time standby / sleep command
                                if is_standby_phrase(txt) or is_standby_phrase(full_in_check):
                                    print(f"[JarvisLive] Standby voice command: '{full_in_check}'")
                                    wake_word_controller.deactivate(reason=f"Spoken: '{full_in_check}'")
                                    continue

                                wake_word_controller.touch()

                        if sc.turn_complete:
                            self.set_speaking(False)
                            wake_word_controller.touch()
                            # Reset viseme timeline after speech ends
                            try:
                                self.ui.avatar.reset_viseme()
                            except Exception:
                                pass

                            full_in = "".join(in_buf).strip()
                            if full_in:
                                self.ui.write_log(f"You: {full_in}")
                            in_buf = []

                            full_out = "".join(out_buf).strip()
                            if full_out:
                                self.ui.write_log(f"INDUS: {full_out}")
                                # If the user asked an informational question or requested information, float Info Card
                                q_lower = full_in.lower() if full_in else ""
                                q_triggers = ["what", "who", "where", "when", "why", "how", "tell", "explain", "search", "kya", "kaun", "kaha", "kab", "kyu", "kaise", "batao", "dhundo", "info", "score", "weather", "about"]
                                if len(full_out) > 25 and (any(w in q_lower for w in q_triggers) or "?" in full_in):
                                    try:
                                        self.ui.show_info_card(query=full_in, result=full_out)
                                    except Exception:
                                        pass
                            out_buf = []

                            if full_in and len(full_in) > 5 and not cancellation_manager.is_cancelled():
                                threading.Thread(
                                    target=_update_memory_async,
                                    args=(full_in, full_out),
                                    daemon=True
                                ).start()

                    if response.tool_call:
                        wake_word_controller.touch()
                        fn_responses = []
                        for fc in response.tool_call.function_calls:
                            print(f"[INDUS] [CALL] {fc.name}")
                            fr = await self._execute_tool(fc)
                            fn_responses.append(fr)
                        await self.session.send_tool_response(
                            function_responses=fn_responses
                        )

        except Exception as e:
            err_str = str(e)
            # Gemini Live intermittent: model returned empty turn — safe to reconnect
            if "model output must contain either output text or tool calls" in err_str:
                print(f"[INDUS] [WARN] Empty model turn (harmless, reconnecting): {err_str}")
                self.ui.write_log("• SYS: [WARN] Empty response from model — reconnecting...")
                return   # let the outer while-True reconnect loop handle it
            print(f"[INDUS] [ERR] Recv: {e}")
            traceback.print_exc()
            raise

    async def _play_audio(self):
        print("[INDUS] [PLAY] Play started")

        stream = sd.RawOutputStream(
            samplerate=RECEIVE_SAMPLE_RATE,
            channels=CHANNELS,
            dtype="int16",
            blocksize=CHUNK_SIZE,
        )
        stream.start()
        try:
            while True:
                chunk = await self.audio_in_queue.get()
                if cancellation_manager.is_cancelled():
                    self.audio_in_queue.task_done()
                    self.set_speaking(False)
                    continue
                self.set_speaking(True)

                # Real-time synchronized lip-sync and audio visualizer with speaker output
                try:
                    rms = compute_pcm_rms(chunk)
                    # Gemini Live outputs 24kHz PCM — normalize with corrected divisor
                    level = min(1.0, rms / 1800.0) if rms > 80.0 else 0.0
                    self.ui.set_audio_level(level)
                    self.ui.avatar.process_audio_chunk(chunk)
                except Exception:
                    pass

                await asyncio.to_thread(stream.write, chunk)
                self.audio_in_queue.task_done()
                if self.audio_in_queue.empty():
                    self.set_speaking(False)
                    self.ui.set_audio_level(0.0)
                    try:
                        self.ui.avatar.stop_speaking()
                    except Exception:
                        pass
        except Exception as e:
            print(f"[INDUS] [ERR] Play: {e}")
            raise
        finally:
            self.set_speaking(False)
            self.ui.set_audio_level(0.0)
            stream.stop()
            stream.close()


    async def run(self):
        client = genai.Client(
            api_key=_get_api_key(),
            http_options={"api_version": "v1beta"}
        )

        while True:
            try:
                print("[INDUS] [CONNECT] Connecting...")
                self.ui.set_state("THINKING")
                config = self._build_config()

                async with (
                    client.aio.live.connect(model=LIVE_MODEL, config=config) as session,
                    asyncio.TaskGroup() as tg,
                ):
                    self.session        = session
                    self._loop          = asyncio.get_event_loop()
                    self.audio_in_queue = asyncio.Queue()
                    self.out_queue      = asyncio.Queue(maxsize=100)

                    print("[INDUS] Connected.")
                    # Publish LLM_CONNECTED so UI and diagnostics can trace session start
                    event_bus.publish(E.LLM_CONNECTED, source="main",
                                      data={"model": LIVE_MODEL, "provider": "gemini_live"})
                    self.ui.set_state("STANDBY")

                    self.ui.write_log("SYS: INDUS online in STANDBY mode (Say 'INDUS' to activate).")

                    # Enforce stored long-term preferences (e.g. Dark Mode)
                    try:
                        from memory.memory_manager import enforce_user_preferences
                        enforce_results = enforce_user_preferences()
                        for action_info in enforce_results:
                            self.ui.write_log(f"• SYS: {action_info}")
                    except Exception as e:
                        print(f"[INDUS] Startup preference check error: {e}")

                    # Start Autonomous Watcher daemon (Jarvis background PC monitor)
                    try:
                        from actions.autonomous_watcher import start_autonomous_watcher
                        start_autonomous_watcher(player_ui=self.ui)
                    except Exception as e:
                        print(f"[INDUS] Autonomous watcher startup error: {e}")

                    # Warmup vision session in background so first screen_process call is instant (not 20s wait)
                    try:
                        from actions.screen_processor import warmup_session
                        threading.Thread(target=warmup_session, args=(self.ui,), daemon=True, name="VisionWarmup").start()
                        print("[INDUS] [WARMUP] Vision warmup started in background")
                    except Exception as e:
                        print(f"[INDUS] Vision warmup error: {e}")

                    tg.create_task(self._send_realtime())
                    tg.create_task(self._listen_audio())
                    tg.create_task(self._receive_audio())
                    tg.create_task(self._play_audio())
                    tg.create_task(self._inactivity_monitor())

                    
            except Exception as e:
                print(f"[JARVIS] [WARN] {e}")
                traceback.print_exc()

            self.set_speaking(False)
            self.ui.set_state("THINKING")
            print("[JARVIS] [RETRY] Reconnecting in 3s...")
            await asyncio.sleep(3)

def main():
    ui = JarvisUI(str(BASE_DIR / "face.png"))

    def runner():
        ui.wait_for_api_key()
        jarvis = JarvisLive(ui)
        try:
            asyncio.run(jarvis.run())
        except KeyboardInterrupt:
            print("\n[STOP] Shutting down...")

    threading.Thread(target=runner, daemon=True).start()
    ui.root.mainloop()


if __name__ == "__main__":
    main()