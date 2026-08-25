# actions/app_ui_navigator.py
"""
INDUS Visual App Navigator & In-App Settings Automation Engine
=============================================================
Autonomously:
1. Launches any application or browser.
2. Visually scans the active window to locate the Settings / Preferences / ⚙️ Gear / Menu button.
3. Clicks into the Settings panel.
4. If a task is specified (e.g. "dark mode on", "change audio output", "clear cache"),
   visually grounds that setting option and executes it.
5. If ambiguous, inspects the visible settings options, speaks to the user in Hinglish,
   and executes the desired setting upon instruction.
"""

from __future__ import annotations
import logging
import time
from typing import Any, Dict, Optional

import pyautogui
pyautogui.FAILSAFE = False

logger = logging.getLogger("IndusAppNavigator")

# Common settings hotkeys per application
APP_SETTINGS_SHORTCUTS = {
    "vscode": "ctrl+,",
    "vs code": "ctrl+,",
    "code": "ctrl+,",
    "visual studio code": "ctrl+,",
    "spotify": "ctrl+p",
    "obsidian": "ctrl+,",
    "slack": "ctrl+,",
    "discord": "user_settings_icon",
    "chrome": "alt+e",
    "google chrome": "alt+e",
    "edge": "alt+f",
    "brave": "alt+e",
}

SETTINGS_GROUNDING_PROMPTS = [
    "Settings icon or gear icon or Preferences button",
    "Settings menu item or options button (three dots / three bars)",
    "Profile or account avatar leading to settings",
    "User settings gear icon in bottom left or top right"
]


def open_and_navigate_settings(
    app_name: str,
    setting_task: str = "",
    player=None,
    speak=None
) -> str:
    """
    1. Opens app.
    2. Visually locates and clicks Settings/Gear.
    3. Executes the requested task or inspects options.
    """
    from actions.open_app import open_app
    from actions.vision_engine import (
        capture_screen,
        extract_ocr_elements,
        ground_ui_element,
        screen_understand,
        vision_click,
    )

    clean_app = (app_name or "").strip()
    if not clean_app:
        return "App name is required for settings navigation."

    if player:
        player.write_log(f"[AppNavigator] Launching {clean_app}...")

    # Step 1: Open the Application
    open_res = open_app({"app_name": clean_app}, player=player)
    time.sleep(2.0)  # Allow window to draw and focus

    # Step 2: Try Application-Specific Fast Shortcut if available
    app_key = clean_app.lower().strip()
    shortcut_used = False
    if app_key in APP_SETTINGS_SHORTCUTS:
        sc = APP_SETTINGS_SHORTCUTS[app_key]
        if "+" in sc:
            parts = sc.split("+")
            pyautogui.hotkey(*parts)
            time.sleep(1.0)
            shortcut_used = True
            if player:
                player.write_log(f"[AppNavigator] Triggered settings shortcut: {sc}")

    # Step 3: Visual Scan for Settings / Gear Icon
    if not shortcut_used:
        if player:
            player.write_log(f"[AppNavigator] Visually locating Settings/Gear icon in {clean_app}...")

        img, screen_w, screen_h = capture_screen()
        clicked_settings = False

        # 3a. Try OCR text match for "Settings" or "Preferences"
        ocr_elements = extract_ocr_elements(img)
        for el in ocr_elements:
            t = el.get("text", "").lower().strip()
            if t in ("settings", "preferences", "options", "config"):
                pyautogui.click(el["cx"], el["cy"])
                clicked_settings = True
                if player:
                    player.write_log(f"[AppNavigator] OCR clicked '{el['text']}' at ({el['cx']}, {el['cy']})")
                time.sleep(1.2)
                break

        # 3b. Try Visual AI Grounding for Gear/Settings Icon
        if not clicked_settings:
            for prompt_target in SETTINGS_GROUNDING_PROMPTS:
                grounding = ground_ui_element(
                    prompt_target,
                    context=f"In {clean_app} window interface",
                    img=img,
                    player=player
                )
                if grounding.get("found") and float(grounding.get("confidence", 0.0)) >= 0.55:
                    cx, cy = grounding["center_x"], grounding["center_y"]
                    pyautogui.click(cx, cy)
                    clicked_settings = True
                    if player:
                        player.write_log(f"[AppNavigator] AI Vision clicked {prompt_target} at ({cx}, {cy})")
                    time.sleep(1.2)
                    break

    # Step 4: Settings are now open -> Inspect or Execute Task
    time.sleep(0.8)

    # If user provided a specific setting task (e.g. "dark mode on", "change download location"):
    if setting_task and setting_task.lower() not in ("ask", "open", "show", "open settings"):
        if player:
            player.write_log(f"[AppNavigator] Executing setting task: '{setting_task}'")

        # Ground and click target setting
        click_res = vision_click(target=setting_task, context=f"Inside {clean_app} settings", player=player)
        return f"{clean_app.title()} open karke settings mein '{setting_task}' par navigate kar diya gaya hai. ({click_res})"

    # If no specific task was given -> Visually inspect visible settings options and ask user!
    vqa_prompt = (
        f"The user just opened settings in {clean_app}. "
        f"List the 3 to 4 main visible setting categories or options visible on screen right now."
    )
    summary = screen_understand(vqa_prompt, player=player)

    msg = (
        f"Main {clean_app.title()} ki settings mein aa gayi hoon. "
        f"Screen par yeh options dikh rahe hain: {summary}. "
        f"Aap yahan kaun sa task ya configuration change karna chahte hain?"
    )
    if player:
        player.write_log(f"[AppNavigator] Settings options inspected: {summary}")

    return msg


def app_settings_navigator(parameters: dict = None, player=None, speak=None) -> str:
    """Main tool entry point for app_settings_navigator."""
    params = parameters or {}
    app_name = params.get("app_name", "")
    setting_task = params.get("setting_task", "") or params.get("task", "")
    return open_and_navigate_settings(
        app_name=app_name,
        setting_task=setting_task,
        player=player,
        speak=speak
    )
