#youtube_video.py
import json
import re
import sys
import time
import threading
import subprocess
import shutil
from pathlib import Path
from datetime import datetime
from urllib.parse import quote_plus

import pyautogui
pyautogui.FAILSAFE = False
import numpy as np

try:
    import requests
    _REQUESTS_OK = True
except ImportError:
    _REQUESTS_OK = False

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    _TRANSCRIPT_OK = True
except ImportError:
    _TRANSCRIPT_OK = False

from config import get_os, is_windows, is_mac, is_linux


def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR        = _get_base_dir()
API_CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

_YT_VIDEO_FILTER = "EgIQAQ%3D%3D"

def _open_url(url: str) -> None:
    try:
        if is_mac():
            subprocess.Popen(["open", url])
        elif is_linux():
            subprocess.Popen(["xdg-open", url])
        else:
            subprocess.Popen(["cmd", "/c", "start", "", url], shell=False)
    except Exception as e:
        print(f"[YouTube] [WARN] open_url failed: {e}")

def _scrape_first_video_url(query: str) -> str | None:

    if not _REQUESTS_OK:
        return None

    search_url = (
        f"https://www.youtube.com/results"
        f"?search_query={quote_plus(query)}"
        f"&sp={_YT_VIDEO_FILTER}"
    )

    try:
        r    = requests.get(search_url, headers=HEADERS, timeout=10)
        html = r.text

        video_ids = re.findall(r'"videoId":"([A-Za-z0-9_-]{11})"', html)

        seen = set()
        for vid in video_ids:
            if vid in seen:
                continue
            seen.add(vid)

            if f'/shorts/{vid}' in html:
                continue
            return f"https://www.youtube.com/watch?v={vid}"

    except Exception as e:
        print(f"[YouTube] [WARN] scrape_first_video_url failed: {e}")

    return None

def _extract_video_id(url: str) -> str | None:
    match = re.search(
        r"(?:v=|\/v\/|youtu\.be\/|\/embed\/|\/shorts\/)([A-Za-z0-9_-]{11})", url
    )
    return match.group(1) if match else None


def _is_valid_youtube_url(url: str) -> bool:
    return bool(re.search(r"(youtube\.com|youtu\.be)", url or ""))


def _ask_for_url(prompt_text: str = "YouTube video URL:") -> str | None:
    try:
        import tkinter as tk
        from tkinter import simpledialog

        root = tk._default_root
        if root is None:
            root = tk.Tk()
            root.withdraw()

        url = simpledialog.askstring("J.A.R.V.I.S", prompt_text, parent=root)
        return url.strip() if url else None
    except Exception as e:
        print(f"[YouTube] [WARN] URL dialog failed: {e}")
        return None


def _get_transcript(video_id: str) -> str | None:
    if not _TRANSCRIPT_OK:
        return None
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        transcript      = None

        lang_priority = ["en", "tr", "de", "fr", "es", "it", "pt", "ru", "ja", "ko", "ar", "zh"]

        try:
            transcript = transcript_list.find_manually_created_transcript(lang_priority)
        except Exception:
            pass

        if transcript is None:
            try:
                transcript = transcript_list.find_generated_transcript(lang_priority)
            except Exception:
                for t in transcript_list:
                    transcript = t
                    break

        if transcript is None:
            return None

        fetched = transcript.fetch()
        return " ".join(entry["text"] for entry in fetched)

    except Exception as e:
        print(f"[YouTube] [WARN] Transcript fetch failed: {e}")
        return None


def _summarize_with_gemini(transcript: str, video_url: str) -> str:
    from or_client import client

    max_chars = 80000
    truncated = transcript[:max_chars] + ("..." if len(transcript) > max_chars else "")

    return client.chat(
        f"Please summarize this YouTube video transcript:\n\n{truncated}",
        system=(
            "You are JARVIS, an AI assistant. "
            "Summarize YouTube video transcripts clearly and concisely. "
            "Structure: 1-sentence overview, then 3-5 key points. "
            "Be direct. Address the user as 'sir'. "
            "Match the language of the transcript."
        ),
        max_tokens=2048,
    )


def _save_summary(content: str, video_url: str) -> str:
    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"youtube_summary_{ts}.txt"
    desktop  = Path.home() / "Desktop"
    desktop.mkdir(parents=True, exist_ok=True)
    filepath = desktop / filename

    header = (
        f"JARVIS -- YouTube Summary\n"
        f"{'-' * 50}\n"
        f"URL    : {video_url}\n"
        f"Date   : {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        f"{'-' * 50}\n\n"
    )
    filepath.write_text(header + content, encoding="utf-8")

    try:
        if is_windows():
            subprocess.Popen(["notepad.exe", str(filepath)])
        elif is_mac():
            subprocess.Popen(["open", "-t", str(filepath)])
        else:
            subprocess.Popen(["xdg-open", str(filepath)])
    except Exception as e:
        print(f"[YouTube] [WARN] Could not open text editor: {e}")

    return str(filepath)


def _scrape_video_info(video_id: str) -> dict:
    if not _REQUESTS_OK:
        return {}
    url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        r    = requests.get(url, headers=HEADERS, timeout=12)
        html = r.text
        info = {}

        for key, pattern in [
            ("title",    r'"title":\{"runs":\[\{"text":"([^"]+)"'),
            ("channel",  r'"ownerChannelName":"([^"]+)"'),
            ("views",    r'"viewCount":"(\d+)"'),
            ("duration", r'"lengthSeconds":"(\d+)"'),
            ("likes",    r'"label":"([0-9,]+ likes)"'),
        ]:
            match = re.search(pattern, html)
            if match:
                raw = match.group(1)
                if key == "views":
                    info[key] = f"{int(raw):,}"
                elif key == "duration":
                    secs = int(raw)
                    info[key] = f"{secs // 60}:{secs % 60:02d}"
                else:
                    info[key] = raw

        return info
    except Exception as e:
        print(f"[YouTube] [WARN] Info scrape failed: {e}")
        return {}


def _scrape_trending(region: str = "TR", max_results: int = 8) -> list[dict]:
    if not _REQUESTS_OK:
        return []
    url = f"https://www.youtube.com/feed/trending?gl={region.upper()}"
    try:
        r    = requests.get(url, headers=HEADERS, timeout=12)
        html = r.text

        titles   = re.findall(r'"title":\{"runs":\[\{"text":"([^"]+)"\}\]', html)
        channels = re.findall(r'"ownerText":\{"runs":\[\{"text":"([^"]+)"', html)

        results, seen = [], set()
        for i, title in enumerate(titles):
            if title in seen or len(title) < 5:
                continue
            seen.add(title)
            channel = channels[i] if i < len(channels) else "Unknown"
            results.append({"rank": len(results) + 1, "title": title, "channel": channel})
            if len(results) >= max_results:
                break

        return results
    except Exception as e:
        print(f"[YouTube] [WARN] Trending scrape failed: {e}")
        return []

def _handle_play(parameters: dict, player) -> str:
    query = parameters.get("query", "").strip()
    if not query:
        return "Please tell me what you'd like to watch, sir."

    if player:
        player.write_log(f"[YouTube] Searching: {query}")

    print(f"[YouTube] Scraping first non-Shorts video for: {query}")

    video_url = _scrape_first_video_url(query)

    if video_url:
        print(f"[YouTube] Opening: {video_url}")
        _open_url(video_url)
        return f"Playing: {query}"

    print(f"[YouTube] Scrape failed, opening filtered search page")
    fallback_url = (
        f"https://www.youtube.com/results"
        f"?search_query={quote_plus(query)}"
        f"&sp={_YT_VIDEO_FILTER}"
    )
    _open_url(fallback_url)
    return f"Opened YouTube search for: {query} (manual selection required)"


def _handle_summarize(parameters: dict, player, speak) -> str:
    if not _TRANSCRIPT_OK:
        return "youtube-transcript-api is not installed. Run: pip install youtube-transcript-api"

    url = _ask_for_url("Please paste the YouTube video URL:")
    if not url:
        return "No URL provided, sir. Summary cancelled."
    if not _is_valid_youtube_url(url):
        return "That doesn't appear to be a valid YouTube URL, sir."

    video_id = _extract_video_id(url)
    if not video_id:
        return "Could not extract video ID from that URL, sir."

    if player:
        player.write_log(f"[YouTube] Summarizing: {url}")
    if speak:
        speak("Fetching the transcript now, sir. One moment.")

    transcript = _get_transcript(video_id)
    if not transcript:
        return "I couldn't retrieve a transcript for that video, sir."

    if speak:
        speak("Transcript retrieved. Generating summary now.")

    try:
        summary = _summarize_with_gemini(transcript, url)
    except Exception as e:
        return f"Summary generation failed, sir: {e}"

    if speak:
        speak(summary)

    if parameters.get("save", False):
        saved_path = _save_summary(summary, url)
        return f"Summary complete and saved to Desktop: {saved_path}"

    return summary


def _handle_get_info(parameters: dict, player, speak) -> str:
    url = parameters.get("url", "").strip()
    if not url:
        url = _ask_for_url("Please paste the YouTube video URL:")
    if not url or not _is_valid_youtube_url(url):
        return "Please provide a valid YouTube URL, sir."

    video_id = _extract_video_id(url)
    if not video_id:
        return "Could not extract video ID, sir."

    if player:
        player.write_log(f"[YouTube] Getting info: {url}")

    info = _scrape_video_info(video_id)
    if not info:
        return "Could not retrieve video information, sir."

    lines = [
        f"{key.capitalize()}: {info[key]}"
        for key in ("title", "channel", "views", "duration", "likes")
        if key in info
    ]
    result = "\n".join(lines)

    if speak:
        speak(f"Here's the video info, sir. {result.replace(chr(10), '. ')}")

    return result


def _handle_trending(parameters: dict, player, speak) -> str:
    region = parameters.get("region", "TR").upper()

    if player:
        player.write_log(f"[YouTube] Trending: {region}")

    trending = _scrape_trending(region=region, max_results=8)
    if not trending:
        return f"Could not fetch trending videos for region {region}, sir."

    lines  = [f"Top trending videos in {region}:"]
    lines += [f"{v['rank']}. {v['title']} -- {v['channel']}" for v in trending]
    result = "\n".join(lines)

    if speak:
        top3   = trending[:3]
        spoken = "Here are the top trending videos, sir. " + ". ".join(
            f"Number {v['rank']}: {v['title']} by {v['channel']}" for v in top3
        )
        speak(spoken)

    return result

_ad_skip_stop_event = threading.Event()

def _ad_skip_worker(player=None):
    """Background worker to check for YouTube skip button without blocking main loop."""
    time.sleep(3.5)
    skip_img_path = _get_base_dir() / "core" / "skip_ad.png"
    for _ in range(20):  # Check for up to 10 seconds (20 * 0.5s)
        if _ad_skip_stop_event.is_set():
            if player:
                player.write_log("[YouTube] Ad skip monitoring stopped.")
            return
        try:
            if skip_img_path.exists():
                loc = pyautogui.locateOnScreen(str(skip_img_path), confidence=0.7)
                if loc:
                    pyautogui.click(pyautogui.center(loc))
                    if player:
                        player.write_log("[YouTube] Ad skipped successfully via template match.")
                    return
        except Exception:
            pass
        time.sleep(0.5)


def _handle_stop(parameters: dict, player, speak=None) -> str:
    """Stop/Pause video and terminate any running ad skip watcher."""
    _ad_skip_stop_event.set()
    try:
        pyautogui.press("k")
        if player:
            player.write_log("[YouTube] Video paused/stopped.")
        return "YouTube playback stopped."
    except Exception as e:
        return f"Could not stop video: {e}"


def _handle_pause(parameters: dict, player, speak=None) -> str:
    """Pause the video."""
    _ad_skip_stop_event.set()
    try:
        pyautogui.press("k")
        return "YouTube video paused."
    except Exception as e:
        return f"Could not pause: {e}"


def _handle_resume(parameters: dict, player, speak=None) -> str:
    """Resume / play the video."""
    try:
        pyautogui.press("k")
        return "YouTube video resumed."
    except Exception as e:
        return f"Could not resume: {e}"


def _handle_close(parameters: dict, player, speak=None) -> str:
    """Close the current YouTube tab."""
    _ad_skip_stop_event.set()
    try:
        if is_mac():
            pyautogui.hotkey("command", "w")
        else:
            pyautogui.hotkey("ctrl", "w")
        return "YouTube tab closed."
    except Exception as e:
        return f"Could not close tab: {e}"


def _handle_mute(parameters: dict, player, speak=None) -> str:
    """Toggle mute on YouTube."""
    try:
        pyautogui.press("m")
        return "YouTube mute toggled."
    except Exception as e:
        return f"Could not toggle mute: {e}"


def _handle_fullscreen(parameters: dict, player, speak=None) -> str:
    """Toggle fullscreen on YouTube."""
    try:
        pyautogui.press("f")
        return "YouTube fullscreen toggled."
    except Exception as e:
        return f"Could not toggle fullscreen: {e}"


def _handle_skip_ad(parameters: dict = None, player=None, speak=None) -> str:
    """Delegate ad-skipping directly to universal_ad_skipper engine."""
    from actions.universal_ad_skipper import universal_ad_skipper
    return universal_ad_skipper(parameters={"action": "skip_ad"}, player=player, speak=speak)


def _handle_set_quality(parameters: dict, player, speak=None) -> str:
    """
    Live screen reading to set YouTube video quality (e.g. 1080p, 720p, 480p, 360p, 240p, 144p, auto).
    Autonomously clicks Settings gear -> Quality -> Target resolution.
    """
    quality = str(parameters.get("quality") or parameters.get("value") or parameters.get("query") or "1080p").lower().strip()
    if player:
        player.write_log(f"[YouTube] Setting quality: {quality}")
    print(f"[YouTube] Live screen reading to set quality to: {quality}")

    try:
        from actions.computer_control import _screen_find
        sw, sh = pyautogui.size()

        # Step 1: Hover over video player to reveal player controls HUD
        pyautogui.moveTo(sw // 2, sh // 2, duration=0.2)
        time.sleep(0.3)

        # Step 2: Live screen read -> Find and click Settings gear icon
        gear_pt = _screen_find("YouTube video player Settings gear icon button at bottom right")
        if gear_pt:
            pyautogui.click(gear_pt[0], gear_pt[1])
            if player:
                player.write_log(f"[YouTube] Clicked Settings gear at {gear_pt}")
        else:
            # Fallback: Click near bottom-right of video
            pyautogui.click(int(sw * 0.72), int(sh * 0.72))
        time.sleep(0.6)

        # Step 3: Live screen read -> Find and click "Quality" menu item
        quality_pt = _screen_find("Quality menu option in YouTube settings popup menu")
        if quality_pt:
            pyautogui.click(quality_pt[0], quality_pt[1])
            if player:
                player.write_log(f"[YouTube] Clicked Quality menu at {quality_pt}")
        time.sleep(0.6)

        # Step 4: Live screen read -> Find and click target resolution
        res_pt = _screen_find(f"{quality} resolution option in YouTube quality selection menu")
        if res_pt:
            pyautogui.click(res_pt[0], res_pt[1])
            if player:
                player.write_log(f"[YouTube] Clicked {quality} at {res_pt}")
        else:
            # Click near top or bottom depending on quality
            pyautogui.click(int(sw * 0.72), int(sh * 0.60))

        time.sleep(0.3)
        # Move mouse away so controls fade
        pyautogui.moveTo(sw // 2, sh // 2)

        return f"Screen ko live scan karke YouTube video quality {quality} par set kar di gayi hai."
    except Exception as e:
        print(f"[YouTube] Quality setting error: {e}")
        return f"YouTube video quality {quality} par set karne ki koshish ki."


def _handle_set_speed(parameters: dict, player, speak=None) -> str:
    """
    Sets playback speed on YouTube player (e.g. 1.25x, 1.5x, 2x, 0.5x, normal) using YouTube hotkeys.
    """
    speed = str(parameters.get("speed") or parameters.get("value") or "normal").lower().strip()
    if player:
        player.write_log(f"[YouTube] Speed: {speed}")

    try:
        if "fast" in speed or "1.5" in speed or "2" in speed or "1.25" in speed:
            pyautogui.hotkey("shift", ">")
            return f"Playback speed fast kar di gayi hai ({speed})."
        elif "slow" in speed or "0.5" in speed or "0.75" in speed:
            pyautogui.hotkey("shift", "<")
            return f"Playback speed slow kar di gayi hai ({speed})."
        else:
            return f"Playback speed: {speed}"
    except Exception as e:
        return f"Could not change speed: {e}"


def _handle_forward(parameters: dict, player, speak=None) -> str:
    """Fast forward YouTube video by N seconds (defaults to 10s or 5s increments)."""
    secs = parameters.get("seconds") or parameters.get("amount") or 10
    try:
        secs = int(re.sub(r"[^\d]", "", str(secs)) or "10")
    except Exception:
        secs = 10

    if player:
        player.write_log(f"[YouTube] Forward: {secs}s")

    try:
        # Use 10-second jumps ('l') or 5-second jumps ('right')
        tens = secs // 10
        remainder = (secs % 10) // 5
        if tens > 0:
            for _ in range(tens):
                pyautogui.press("l")
                time.sleep(0.05)
        if remainder > 0:
            for _ in range(remainder):
                pyautogui.press("right")
                time.sleep(0.05)
        if tens == 0 and remainder == 0:
            pyautogui.press("right")
        return f"Gaane/video ko {secs} seconds forward kar diya hai."
    except Exception as e:
        return f"Forward failed: {e}"


def _handle_rewind(parameters: dict, player, speak=None) -> str:
    """Rewind YouTube video by N seconds (defaults to 10s or 5s increments)."""
    secs = parameters.get("seconds") or parameters.get("amount") or 10
    try:
        secs = int(re.sub(r"[^\d]", "", str(secs)) or "10")
    except Exception:
        secs = 10

    if player:
        player.write_log(f"[YouTube] Rewind: {secs}s")

    try:
        tens = secs // 10
        remainder = (secs % 10) // 5
        if tens > 0:
            for _ in range(tens):
                pyautogui.press("j")
                time.sleep(0.05)
        if remainder > 0:
            for _ in range(remainder):
                pyautogui.press("left")
                time.sleep(0.05)
        if tens == 0 and remainder == 0:
            pyautogui.press("left")
        return f"Gaane/video ko {secs} seconds peeche (rewind) kar diya hai."
    except Exception as e:
        return f"Rewind failed: {e}"


_ACTION_MAP = {
    "play":             _handle_play,
    "search":           _handle_play,
    "search_video":     _handle_play,
    "find":             _handle_play,
    "summarize":        _handle_summarize,

    "get_info":         _handle_get_info,
    "trending":         _handle_trending,
    "stop":             _handle_stop,
    "terminate":        _handle_stop,
    "pause":            _handle_pause,
    "resume":           _handle_resume,
    "unpause":          _handle_resume,
    "forward":          _handle_forward,
    "fast_forward":     _handle_forward,
    "rewind":           _handle_rewind,
    "back":             _handle_rewind,
    "seek":             _handle_forward,
    "close":            _handle_close,
    "close_tab":        _handle_close,
    "mute":             _handle_mute,
    "fullscreen":       _handle_fullscreen,
    "set_quality":      _handle_set_quality,
    "quality":          _handle_set_quality,
    "change_quality":   _handle_set_quality,
    "set_speed":        _handle_set_speed,
    "speed":            _handle_set_speed,
    "skip_ad":          _handle_skip_ad,
    "skip_ads":         _handle_skip_ad,
}


def youtube_video(
    parameters:     dict,
    response=None,
    player=None,
    session_memory=None,
    speak=None,
) -> str:
    params = parameters or {}
    action = params.get("action", "play").lower().strip()

    if player:
        player.write_log(f"[YouTube] Action: {action}")
    print(f"[YouTube] [>] Action: {action}  Params: {params}")

    # Special action: play and then auto-skip ads in non-blocking background thread
    if action in ("play_and_skip_ad", "play_skip_ad", "play_and_skip"):
        query = params.get("query", "").strip()
        if not query:
            return "Please tell me what song or video to play."

        # Reset stop event
        _ad_skip_stop_event.clear()

        # Step 1: Play the video via normal play
        play_result = _handle_play(params, player)

        if player:
            player.write_log("[YouTube] Monitoring for skippable ads in background...")
        if speak:
            speak("Playing now. I'll keep an eye out for any ads in the background.")

        # Step 2: Start non-blocking background worker
        t = threading.Thread(target=_ad_skip_worker, args=(player,), daemon=True)
        t.start()

        # Step 3: Return immediately to prevent blocking Gemini Live session
        return f"{play_result}. Ad monitoring is active in background."

    handler = _ACTION_MAP.get(action)
    if handler is None:
        return (
            f"Unknown YouTube action: '{action}'. "
            "Available: play, play_and_skip_ad, stop, pause, resume, close, summarize, get_info, trending."
        )

    try:
        if action in ("play", "search", "search_video", "find"):
            return handler(params, player) or "Done."
        return handler(params, player, speak) or "Done."

    except Exception as e:
        print(f"[YouTube] Error in {action}: {e}")
        return f"YouTube {action} failed: {e}"