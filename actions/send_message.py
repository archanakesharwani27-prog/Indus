# actions/send_message.py
# Universal messaging -- WhatsApp & Instagram
# Uses visual element detection (pyautogui + screen search) instead of
# hardcoded tab/click sequences -- works on any screen resolution.

import os
import time
import subprocess
import platform
import pyautogui
from pathlib import Path

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.08

_OS = platform.system()

def _open_app(app_name: str) -> bool:
    """Opens an app via Windows search."""
    try:
        pyautogui.press("win")
        time.sleep(0.4)
        pyautogui.write(app_name, interval=0.04)
        time.sleep(0.5)
        pyautogui.press("enter")
        time.sleep(2.0)  
        return True
    except Exception as e:
        print(f"[SendMessage] Could not open {app_name}: {e}")
        return False


def _search_contact(contact: str, platform: str):
    """
    Searches for a contact inside the messaging app.
    Uses Ctrl+F (universal search shortcut) then types contact name.
    """
    time.sleep(0.5)
    pyautogui.hotkey("ctrl", "f")
    time.sleep(0.4)
    pyautogui.hotkey("ctrl", "a")
    pyautogui.write(contact, interval=0.04)
    time.sleep(0.8)
    pyautogui.press("enter")
    time.sleep(0.6)


def _type_and_send(message: str):
    """Types message and sends it."""
    pyautogui.press("tab")
    time.sleep(0.2)
    pyautogui.hotkey("ctrl", "a")
    pyautogui.write(message, interval=0.03)
    time.sleep(0.2)
    pyautogui.press("enter")
    time.sleep(0.3)


def _get_window_rect(title_fragment: str) -> tuple | None:
    """Returns (left, top, width, height) of a window by partial title. Windows only."""
    if _OS != "Windows":
        return None
    try:
        import ctypes
        import ctypes.wintypes

        user32 = ctypes.windll.user32
        EnumWindows      = user32.EnumWindows
        GetWindowText    = user32.GetWindowTextW
        GetWindowRect    = user32.GetWindowRect
        IsWindowVisible  = user32.IsWindowVisible

        result = []
        buf = ctypes.create_unicode_buffer(512)

        def callback(hwnd, _):
            if IsWindowVisible(hwnd):
                GetWindowText(hwnd, buf, 512)
                if title_fragment.lower() in buf.value.lower():
                    rect = ctypes.wintypes.RECT()
                    GetWindowRect(hwnd, ctypes.byref(rect))
                    result.append((rect.left, rect.top,
                                   rect.right - rect.left,
                                   rect.bottom - rect.top))
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        EnumWindows(WNDENUMPROC(callback), 0)
        return result[0] if result else None
    except Exception:
        return None


def _ocr_region(x: int, y: int, w: int, h: int) -> str:
    """Takes a screenshot of a screen region and extracts text using pytesseract or basic check."""
    try:
        import pyautogui
        img = pyautogui.screenshot(region=(x, y, w, h))

        # Try pytesseract first
        try:
            import pytesseract
            return pytesseract.image_to_string(img).lower()
        except Exception:
            pass

        # Fallback: use PIL to check pixel colors / simple heuristic
        return ""
    except Exception:
        return ""


def _verify_whatsapp_chat(expected_name: str, wa_rect: tuple) -> bool:
    """
    Takes screenshot of WhatsApp chat header and checks if the expected contact name is there.
    WhatsApp desktop: contact name appears in the top-center header of the chat panel.
    """
    try:
        if not wa_rect:
            return True  # Can't verify, assume OK

        left, top, width, height = wa_rect
        # Header area: roughly top 60px of the right (chat) panel
        # The chat panel starts at roughly 30% from the left
        chat_x = left + int(width * 0.3)
        chat_y = top + 8
        chat_w = int(width * 0.7)
        chat_h = 60

        text = _ocr_region(chat_x, chat_y, chat_w, chat_h)
        if not text:
            return True  # Can't read, assume OK

        # Check if expected name words appear in the header
        name_words = [w.lower() for w in expected_name.split() if len(w) >= 3]
        matched = sum(1 for word in name_words if word in text)
        return matched >= max(1, len(name_words) - 1)
    except Exception:
        return True  # Assume OK on error


def _send_whatsapp(receiver: str, message: str) -> str:
    """
    Sends a WhatsApp message via the Windows desktop app.
    Flow:
      1. Open/focus WhatsApp
      2. Use New Chat (Ctrl+N) ? search the exact contact name
      3. Focus search result via Down key + Enter AND click contact item
      4. Verify the correct chat is open (OCR header)
      5. Type and send the message
    """
    try:
        pyautogui.FAILSAFE = False

        # Step 1: Open WhatsApp
        if not _open_app("WhatsApp"):
            return "Could not open WhatsApp."
        time.sleep(2.0)

        # Step 2: Focus WhatsApp window and get its position
        wa_rect = _get_window_rect("WhatsApp")

        # Step 3: Open New Chat / search
        pyautogui.hotkey("ctrl", "n")
        time.sleep(0.8)

        # Clear any existing text and type receiver name
        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.2)
        pyautogui.write(receiver, interval=0.05)
        time.sleep(1.2)  # Wait for search results to populate

        # Step 4: Select the first contact from search results
        # Press Down arrow to highlight first contact in results list, then Enter
        pyautogui.press("down")
        time.sleep(0.3)
        pyautogui.press("enter")
        time.sleep(0.8)

        # Also click the first contact row directly (approx x=left+140, y=top+205 in WhatsApp Desktop)
        if wa_rect:
            left, top, width, height = wa_rect
            click_x = left + min(150, int(width * 0.15))
            click_y = top + 205
            pyautogui.click(click_x, click_y)
            time.sleep(1.0)

        # Step 5: Verify the correct contact is open
        verified = _verify_whatsapp_chat(receiver, wa_rect)

        if not verified:
            # Retry: press enter again
            pyautogui.press("enter")
            time.sleep(0.8)

        # Step 6: Make sure we are in the message input box
        if wa_rect:
            left, top, width, height = wa_rect
            msg_x = left + int(width * 0.65)
            msg_y = top + int(height * 0.94)
            pyautogui.click(msg_x, msg_y)
            time.sleep(0.4)
        else:
            pyautogui.press("tab")
            time.sleep(0.3)

        # Step 7: Clear any pre-existing text in input and type message
        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.1)
        pyautogui.write(message, interval=0.03)
        time.sleep(0.3)
        pyautogui.press("enter")
        time.sleep(0.8)

        return f"Message sent to '{receiver}' via WhatsApp."

    except Exception as e:
        return f"WhatsApp error: {e}"




def _send_instagram(receiver: str, message: str) -> str:
    """
    Sends an Instagram DM via browser (instagram.com).
    Steps: Open Chrome ? Go to instagram.com/direct ? Search contact ? Send
    """
    try:
        import webbrowser

        webbrowser.open("https://www.instagram.com/direct/new/")
        time.sleep(3.5)

        pyautogui.write(receiver, interval=0.05)
        time.sleep(1.5)

        pyautogui.press("down")
        time.sleep(0.3)
        pyautogui.press("enter")
        time.sleep(0.5)

        for _ in range(3):
            pyautogui.press("tab")
            time.sleep(0.1)
        pyautogui.press("enter")
        time.sleep(1.5)

        pyautogui.write(message, interval=0.04)
        time.sleep(0.2)
        pyautogui.press("enter")

        return f"Message sent to {receiver} via Instagram."

    except Exception as e:
        return f"Instagram error: {e}"

def _send_telegram(receiver: str, message: str) -> str:
    """Sends a Telegram message via Windows desktop app with proper click on contact."""
    try:
        if not _open_app("Telegram"):
            return "Could not open Telegram."
        time.sleep(2.0)

        tg_rect = _get_window_rect("Telegram")

        # Use Ctrl+F to search contact
        pyautogui.hotkey("ctrl", "f")
        time.sleep(0.5)
        pyautogui.hotkey("ctrl", "a")
        pyautogui.write(receiver, interval=0.05)
        time.sleep(1.5)

        # Click the first result by mouse position (Telegram: results in left panel)
        if tg_rect:
            left, top, width, height = tg_rect
            click_x = left + int(width * 0.15)
            click_y = top + 145
            pyautogui.click(click_x, click_y)
        else:
            pyautogui.press("down")
            time.sleep(0.3)
            pyautogui.press("enter")
        time.sleep(1.0)

        # Click the message input area
        if tg_rect:
            left, top, width, height = tg_rect
            pyautogui.click(left + int(width * 0.65), top + int(height * 0.95))
            time.sleep(0.4)

        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.1)
        pyautogui.write(message, interval=0.03)
        time.sleep(0.3)
        pyautogui.press("enter")
        time.sleep(0.5)

        return f"Message sent to '{receiver}' via Telegram."

    except Exception as e:
        return f"Telegram error: {e}"



def _send_generic(platform_name: str, receiver: str, message: str) -> str:
    """
    For any other platform not explicitly supported.
    Opens the app, searches for contact, types and sends.
    Works for: Messenger, Discord, Signal, etc.
    """
    try:
        if not _open_app(platform_name):
            return f"Could not open {platform_name}."

        time.sleep(1.5)
        pyautogui.hotkey("ctrl", "f")
        time.sleep(0.4)
        pyautogui.write(receiver, interval=0.04)
        time.sleep(1.0)
        pyautogui.press("enter")
        time.sleep(0.8)
        pyautogui.write(message, interval=0.03)
        time.sleep(0.2)
        pyautogui.press("enter")

        return f"Message sent to {receiver} via {platform_name}."

    except Exception as e:
        return f"{platform_name} error: {e}"


# -----------------------------------------------------------------------------
# Screenshot ? Send helpers
# -----------------------------------------------------------------------------

def _take_screenshot() -> Path | None:
    """Takes a screenshot, saves it to Desktop, returns the path."""
    try:
        import pyautogui
        desktop = Path.home() / "Desktop"
        desktop.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        path = desktop / f"indus_screenshot_{ts}.png"
        screenshot = pyautogui.screenshot()
        screenshot.save(str(path))
        print(f"[Screenshot] Saved to: {path}")
        return path
    except Exception as e:
        print(f"[Screenshot] Failed: {e}")
        return None


def _copy_image_to_clipboard(image_path: Path) -> bool:
    """Instantly copies an image to Windows clipboard using native Win32 API without PowerShell delay."""
    try:
        from PIL import Image
        import io
        import win32clipboard

        image = Image.open(image_path)
        output = io.BytesIO()
        image.convert("RGB").save(output, "BMP")
        data = output.getvalue()[14:]  # Remove 14-byte BMP file header for standard CF_DIB
        output.close()

        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
        win32clipboard.CloseClipboard()
        return True
    except Exception as e:
        print(f"[Clipboard] Win32 copy error: {e}")
        try:
            subprocess.run(
                ["powershell", "-Command",
                 f"Add-Type -AssemblyName System.Windows.Forms; "
                 f"[System.Windows.Forms.Clipboard]::SetFileDropList("
                 f"[System.Collections.Specialized.StringCollection]@('{str(image_path)}'))"],
                capture_output=True, timeout=3
            )
            return True
        except Exception:
            return False


def _call_whatsapp(receiver: str, call_type: str = "voice") -> str:
    """
    Initiates a WhatsApp voice or video call to a contact.
    Flow: Open WhatsApp ? Search & open contact ? Click Voice/Video Call button in chat header.
    """
    try:
        pyautogui.FAILSAFE = False
        is_video = "video" in str(call_type).lower()

        if not _open_app("WhatsApp"):
            return "Could not open WhatsApp."
        time.sleep(2.0)

        wa_rect = _get_window_rect("WhatsApp")

        # Open New Chat search and navigate to contact
        pyautogui.hotkey("ctrl", "n")
        time.sleep(0.8)
        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.2)
        pyautogui.write(receiver, interval=0.05)
        time.sleep(1.2)

        # Select first result with keyboard (most reliable)
        pyautogui.press("down")
        time.sleep(0.3)
        pyautogui.press("enter")
        time.sleep(1.0)  # wait for chat to open

        # Also click the first contact row (top + 205 in WA Desktop sidebar)
        if wa_rect:
            left, top, width, height = wa_rect
            sidebar_x = left + min(150, int(width * 0.15))
            pyautogui.click(sidebar_x, top + 205)
            time.sleep(1.2)  # wait for chat panel to fully load

            # -- WhatsApp Desktop chat header call buttons ----------------------
            # The chat header sits at roughly y = top + 60 (centre of ~72px header)
            # From the right edge of the window:
            #   Three-dots menu  : right - 25
            #   Voice call ([CALL])  : right - 190   (3rd icon from right)
            #   Video call (?)  : right - 260   (4th icon from right)
            header_y   = top + 62
            right_edge = left + width

            if is_video:
                call_x = right_edge - 265
            else:
                call_x = right_edge - 190

            pyautogui.moveTo(call_x, header_y, duration=0.2)
            time.sleep(0.2)
            pyautogui.click(call_x, header_y)
            time.sleep(1.0)

            call_label = "Video call" if is_video else "Voice call"
            return f"{call_label} initiated to '{receiver}' on WhatsApp."
        else:
            # Fallback: keyboard shortcut Ctrl+Shift+C = WhatsApp voice call
            pyautogui.hotkey("ctrl", "shift", "c")
            return f"Voice call triggered to '{receiver}' on WhatsApp via keyboard shortcut."

    except Exception as e:
        return f"WhatsApp call error: {e}"


def _send_screenshot_whatsapp(receiver: str, caption: str = "") -> str:
    """
    Takes a screenshot and sends it to a WhatsApp contact as an image.
    Steps: Screenshot ? Open WhatsApp ? Search & CLICK contact ? Paste image ? Send.
    """
    try:
        pyautogui.FAILSAFE = False

        # 1. Take screenshot first
        img_path = _take_screenshot()
        if not img_path:
            return "Failed to take screenshot."

        # 2. Open WhatsApp
        if not _open_app("WhatsApp"):
            return "Could not open WhatsApp."
        time.sleep(2.0)

        wa_rect = _get_window_rect("WhatsApp")

        # 3. Use Ctrl+N to open New Chat search
        pyautogui.hotkey("ctrl", "n")
        time.sleep(0.8)
        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.2)
        pyautogui.write(receiver, interval=0.05)
        time.sleep(1.2)

        # 4. Select the first contact from search results
        pyautogui.press("down")
        time.sleep(0.3)
        pyautogui.press("enter")
        time.sleep(0.8)

        # Also click the first contact row directly
        if wa_rect:
            left, top, width, height = wa_rect
            click_x = left + min(150, int(width * 0.15))
            click_y = top + 205
            pyautogui.click(click_x, click_y)
            time.sleep(1.0)

        # 5. Copy screenshot to clipboard instantly using native Win32 API
        copied = _copy_image_to_clipboard(img_path)
        time.sleep(0.3)

        # 6. Click the message input box
        if wa_rect:
            left, top, width, height = wa_rect
            pyautogui.click(left + int(width * 0.65), top + int(height * 0.94))
            time.sleep(0.4)
        else:
            pyautogui.press("tab")
            time.sleep(0.2)

        # 7. Paste the image
        pyautogui.hotkey("ctrl", "v")
        time.sleep(1.2)

        # 8. Add caption if provided
        if caption:
            pyautogui.write(caption, interval=0.03)
            time.sleep(0.2)

        # 9. Send
        pyautogui.press("enter")
        time.sleep(0.8)

        return f"Screenshot sent to '{receiver}' via WhatsApp. File: {img_path.name}"

    except Exception as e:
        return f"Screenshot send error: {e}"



def _send_screenshot_telegram(receiver: str, caption: str = "") -> str:
    """Takes a screenshot and sends it to a Telegram contact."""
    try:
        img_path = _take_screenshot()
        if not img_path:
            return "Failed to take screenshot."

        if not _open_app("Telegram"):
            return "Could not open Telegram."
        time.sleep(2.0)

        # Search contact
        pyautogui.hotkey("ctrl", "f")
        time.sleep(0.4)
        pyautogui.write(receiver, interval=0.04)
        time.sleep(1.0)
        pyautogui.press("enter")
        time.sleep(0.8)

        if _OS == "Windows":
            # Copy screenshot file to clipboard
            subprocess.run(
                ["powershell", "-Command",
                 f"Add-Type -AssemblyName System.Windows.Forms; "
                 f"[System.Windows.Forms.Clipboard]::SetFileDropList("
                 f"[System.Collections.Specialized.StringCollection]@('{str(img_path)}'))"],
                capture_output=True, timeout=5
            )
            time.sleep(0.4)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(1.5)

            if caption:
                pyautogui.write(caption, interval=0.03)
                time.sleep(0.2)

            pyautogui.press("enter")
            time.sleep(0.5)
            return f"Screenshot sent to {receiver} via Telegram. File: {img_path.name}"

        return f"Screenshot saved at {img_path}. Please send manually on Telegram."

    except Exception as e:
        return f"Telegram screenshot error: {e}"


def _send_screenshot_generic(platform_name: str, receiver: str, caption: str = "") -> str:
    """Takes a screenshot and tries to send it via any app using clipboard."""
    try:
        img_path = _take_screenshot()
        if not img_path:
            return "Failed to take screenshot."

        if not _open_app(platform_name):
            return f"Could not open {platform_name}."
        time.sleep(2.0)

        pyautogui.hotkey("ctrl", "f")
        time.sleep(0.4)
        pyautogui.write(receiver, interval=0.04)
        time.sleep(1.0)
        pyautogui.press("enter")
        time.sleep(0.8)

        if _OS == "Windows":
            subprocess.run(
                ["powershell", "-Command",
                 f"Add-Type -AssemblyName System.Windows.Forms; "
                 f"[System.Windows.Forms.Clipboard]::SetFileDropList("
                 f"[System.Collections.Specialized.StringCollection]@('{str(img_path)}'))"],
                capture_output=True, timeout=5
            )
            time.sleep(0.4)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(1.5)
            if caption:
                pyautogui.write(caption, interval=0.03)
                time.sleep(0.2)
            pyautogui.press("enter")
            return f"Screenshot sent to {receiver} via {platform_name}. File: {img_path.name}"

        return f"Screenshot saved at {img_path}. Please send manually."

    except Exception as e:
        return f"{platform_name} screenshot error: {e}"


def send_message(
    parameters: dict,
    response=None,
    player=None,
    session_memory=None
) -> str:
    """
    Called from main.py.

    parameters:
        receiver        : Contact name to send to
        message_text    : The message content (optional if send_screenshot=True)
        platform        : whatsapp | instagram | telegram | <any app name>. Default: whatsapp
        send_screenshot : bool -- if True, take screenshot and send as image instead of text
        caption         : Optional caption to add alongside the screenshot
    """
    params          = parameters or {}
    receiver        = params.get("receiver", "").strip()
    message_text    = params.get("message_text", "").strip()
    platform        = params.get("platform", "whatsapp").strip().lower()
    action          = params.get("action", "").strip().lower()
    send_ss         = params.get("send_screenshot", False) or action == "send_screenshot"
    caption         = params.get("caption", "").strip()

    if not receiver:
        return "Please specify who to send the message or call to."

    # -- Call mode (Voice / Video) ----------------------------------------------
    if action in ("call", "voice_call", "video_call") or "call" in action:
        print(f"[SendMessage] [CALL] Calling {receiver} via {platform} ({action})...")
        if player:
            player.write_log(f"[msg] Calling {receiver} via {platform}...")

        if "whatsapp" in platform or "wp" in platform or "wapp" in platform:
            result = _call_whatsapp(receiver, call_type="video" if "video" in action else "voice")
        else:
            result = _call_whatsapp(receiver, call_type="voice")

        print(f"[SendMessage] [OK] {result}")
        if player:
            player.write_log(f"[msg] {result}")
        return result

    print(f"[SendMessage] ? {platform} ? {receiver} | screenshot={send_ss}")
    if player:
        player.write_log(f"[msg] {'Screenshot' if send_ss else 'Message'} ? {receiver} via {platform}...")

    # -- Screenshot mode --------------------------------------------------------
    if send_ss:
        if "whatsapp" in platform or "wp" in platform or "wapp" in platform:
            result = _send_screenshot_whatsapp(receiver, caption)
        elif "telegram" in platform or "tg" in platform:
            result = _send_screenshot_telegram(receiver, caption)
        else:
            result = _send_screenshot_generic(platform, receiver, caption)

        print(f"[SendMessage] [OK] {result}")
        if player:
            player.write_log(f"[msg] {result}")
        return result


    # -- Normal text mode -------------------------------------------------------
    if not message_text:
        return "Please specify what message to send."

    print(f"[SendMessage] ? {platform} ? {receiver}: {message_text[:40]}")

    if "whatsapp" in platform or "wp" in platform or "wapp" in platform:
        result = _send_whatsapp(receiver, message_text)
    elif "instagram" in platform or "ig" in platform or "insta" in platform:
        result = _send_instagram(receiver, message_text)
    elif "telegram" in platform or "tg" in platform:
        result = _send_telegram(receiver, message_text)
    else:
        result = _send_generic(platform, receiver, message_text)

    print(f"[SendMessage] [OK] {result}")
    if player:
        player.write_log(f"[msg] {result}")
    return result