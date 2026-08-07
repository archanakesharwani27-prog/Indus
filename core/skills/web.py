"""
Web Skills - Browser control, search, YouTube, WhatsApp, Weather (PC-side only)
Uses Playwright for actual automation when available.
"""

import webbrowser
import urllib.parse
import subprocess
import asyncio
import requests
from typing import List, Dict, Any
from core.skills.base import BaseSkill, SkillParameter


class OpenURLSkill(BaseSkill):
    """Open a URL in the default browser."""
    
    @property
    def name(self) -> str:
        return "web.open_url"
    
    @property
    def description(self) -> str:
        return "Open a website or URL in the default browser"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="url",
                type="string",
                description="URL to open (will add https:// if missing)",
                required=True,
            ),
            SkillParameter(
                name="browser",
                type="string",
                description="Browser to use (optional)",
                required=False,
                default="",
            ),
        ]
    
    @property
    def category(self) -> str:
        return "web"
    
    @property
    def examples(self) -> List[str]:
        return [
            "Open google.com",
            "Go to github.com",
            "Open https://youtube.com",
        ]
    
    def execute(self, url: str, browser: str = "") -> str:
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        
        try:
            if browser:
                browser_path = self._get_browser_path(browser)
                if browser_path:
                    subprocess.Popen([browser_path, url])
                else:
                    webbrowser.open(url)
            else:
                webbrowser.open(url)
            return f"Opened {url}"
        except Exception as e:
            return f"Failed to open URL: {e}"
    
    def _get_browser_path(self, browser: str) -> str:
        browser = browser.lower()
        paths = {
            "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            "chrome": r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            "firefox": r"C:\Program Files\Mozilla Firefox\firefox.exe",
            "edge": r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        }
        return paths.get(browser, "")


class SearchSkill(BaseSkill):
    """Web search - opens browser, gets AI summary."""

    @property
    def name(self) -> str:
        return "web.search"

    @property
    def description(self) -> str:
        return "Search the web and get AI summary"

    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="query",
                type="string",
                description="Search query",
                required=True,
            ),
            SkillParameter(
                name="engine",
                type="string",
                description="Search engine",
                required=False,
                default="duckduckgo",
                enum=["duckduckgo", "google", "bing", "yahoo"],
            ),
        ]

    @property
    def category(self) -> str:
        return "web"

    @property
    def examples(self) -> List[str]:
        return [
            "Search for python async await tutorial",
            "Weather today in delhi",
            "Find restaurants near me",
        ]

    def execute(self, query: str, engine: str = "duckduckgo") -> str:
        """Search web, get AI summary."""
        search_urls = {
            "duckduckgo": "https://duckduckgo.com/?q={}",
            "google": "https://www.google.com/search?q={}",
            "bing": "https://www.bing.com/search?q={}",
            "yahoo": "https://search.yahoo.com/search?p={}",
        }

        url_template = search_urls.get(engine, search_urls["duckduckgo"])
        encoded_query = urllib.parse.quote(query)
        url = url_template.format(encoded_query)

        # Open browser for reference
        webbrowser.open(url)

        # The LLM (NVIDIA Nemotron) provides the actual answer from its knowledge
        response = f"Opened {engine} search for '{query}'. I can also answer from my knowledge - just ask me directly."

        return response


class YouTubePlaySkill(BaseSkill):
    """Search and play on YouTube - tries Playwright automation first, then browser."""
    
    @property
    def name(self) -> str:
        return "web.youtube_play"
    
    @property
    def description(self) -> str:
        return "Search and play a video on YouTube - uses browser automation to actually play"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="query",
                type="string",
                description="Video search query",
                required=True,
            ),
            SkillParameter(
                name="headless",
                type="boolean",
                description="Run browser in headless mode",
                required=False,
                default=False,
            ),
        ]
    
    @property
    def category(self) -> str:
        return "web"
    
    @property
    def examples(self) -> List[str]:
        return [
            "Play despacito on YouTube",
            "YouTube cat videos",
            "Watch python tutorial on YouTube",
        ]
    
    def execute(self, query: str, headless: bool = False) -> str:
        # Try Playwright automation first
        try:
            from core.automation.playwright_automation import play_youtube_song
            result = asyncio.run(play_youtube_song(query, headless=headless))
            if result.get("success"):
                return f"Playing '{query}' on YouTube (browser automation)"
        except ImportError:
            pass
        except Exception as e:
            print(f"Playwright automation failed: {e}")
        
        # Fallback to browser
        encoded_query = urllib.parse.quote(query)
        url = f"https://www.youtube.com/results?search_query={encoded_query}&sp=EgIQAQ%253D%253D"
        webbrowser.open(url)
        return f"Opened YouTube search for: {query} (automation not available)"


class YouTubeMusicSkill(BaseSkill):
    """Play music on YouTube Music (PC browser)."""
    
    @property
    def name(self) -> str:
        return "web.youtube_music"
    
    @property
    def description(self) -> str:
        return "Play music on YouTube Music in browser"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="query",
                type="string",
                description="Song/artist to play",
                required=True,
            ),
        ]
    
    @property
    def category(self) -> str:
        return "web"
    
    @property
    def examples(self) -> List[str]:
        return [
            "Play shape of you on YouTube Music",
            "YouTube Music playlist lofi",
        ]
    
    def execute(self, query: str) -> str:
        encoded_query = urllib.parse.quote(query)
        url = f"https://music.youtube.com/search?q={encoded_query}"
        webbrowser.open(url)
        return f"Opened YouTube Music for: {query}"


class WhatsAppPCSkill(BaseSkill):
    """Open WhatsApp Web on PC and send messages using browser automation."""
    
    @property
    def name(self) -> str:
        return "web.whatsapp_pc"
    
    @property
    def description(self) -> str:
        return "Open WhatsApp Web on PC and send messages using browser automation"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="contact",
                type="string",
                description="Contact name or phone number",
                required=True,
            ),
            SkillParameter(
                name="message",
                type="string",
                description="Message to send",
                required=True,
            ),
            SkillParameter(
                name="open_only",
                type="boolean",
                description="Only open WhatsApp Web without sending",
                required=False,
                default=False,
            ),
        ]
    
    @property
    def category(self) -> str:
        return "web"
    
    @property
    def examples(self) -> List[str]:
        return [
            "Send WhatsApp to mom hello",
            "Open WhatsApp Web",
            "WhatsApp dad happy birthday",
        ]
    
    def execute(self, contact: str, message: str = "", open_only: bool = False) -> str:
        # Try Playwright automation first
        try:
            from core.automation.playwright_automation import send_whatsapp_message
            result = asyncio.run(send_whatsapp_message(contact, message))
            if result.get("success"):
                return f"Sent WhatsApp message to {contact} via browser automation"
        except ImportError:
            pass
        except Exception as e:
            print(f"Playwright WhatsApp automation failed: {e}")
        
        # Fallback to opening WhatsApp Web
        webbrowser.open("https://web.whatsapp.com/")
        
        if open_only or not message:
            return "Opened WhatsApp Web. Please scan QR code if not already logged in."
        
        # Open chat with pre-filled message
        encoded_message = urllib.parse.quote(message)
        chat_url = f"https://web.whatsapp.com/send?text={urllib.parse.quote(message)}"
        webbrowser.open(chat_url)
        
        return f"Opened WhatsApp Web chat for '{contact}'. Please send manually."


class WhatsAppOpenSkill(BaseSkill):
    """Open WhatsApp Web on PC."""
    
    @property
    def name(self) -> str:
        return "web.whatsapp_open"
    
    @property
    def description(self) -> str:
        return "Open WhatsApp Web on PC"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="wait_for_login",
                type="boolean",
                description="Wait for QR code scan",
                required=False,
                default=True,
            ),
        ]
    
    @property
    def category(self) -> str:
        return "web"
    
    @property
    def examples(self) -> List[str]:
        return [
            "Open WhatsApp Web",
            "Launch WhatsApp on PC",
        ]
    
    def execute(self, wait_for_login: bool = True) -> str:
        webbrowser.open("https://web.whatsapp.com/")
        if wait_for_login:
            return "Opened WhatsApp Web. Please scan QR code with your phone if not already logged in."
        return "Opened WhatsApp Web."


class WeatherSkill(BaseSkill):
    """Get real-time weather using wttr.in (free, no API key)."""

    @property
    def name(self) -> str:
        return "web.weather"

    @property
    def description(self) -> str:
        return "Get current weather for any city using wttr.in"

    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="city",
                type="string",
                description="City name (e.g., Prayagraj, Delhi, Mumbai)",
                required=True,
            ),
        ]

    @property
    def category(self) -> str:
        return "web"

    @property
    def examples(self) -> List[str]:
        return [
            "Weather in Prayagraj",
            "Aaj Prayagraj ka weather kaisa hai",
            "Temperature in Mumbai",
        ]

    def execute(self, city: str) -> str:
        try:
            # Use wttr.in for free weather (no API key needed)
            url = f"https://wttr.in/{urllib.parse.quote(city)}?format=j1"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            current = data.get("current_condition", [{}])[0]
            temp_c = current.get("temp_C", "N/A")
            temp_f = current.get("temp_F", "N/A")
            condition = current.get("weatherDesc", [{}])[0].get("value", "Unknown")
            humidity = current.get("humidity", "N/A")
            wind_kmph = current.get("windspeedKmph", "N/A")
            feels_like = current.get("FeelsLikeC", "N/A")

            # Get location info
            nearest = data.get("nearest_area", [{}])[0]
            area_name = nearest.get("areaName", [{}])[0].get("value", city)
            country = nearest.get("country", [{}])[0].get("value", "")

            weather_text = (
                f"Weather in {area_name}, {country}: "
                f"{condition}, {temp_c}°C (feels like {feels_like}°C), "
                f"Humidity: {humidity}%, Wind: {wind_kmph} km/h"
            )

            return weather_text

        except Exception as e:
            error_msg = f"Failed to get weather for {city}: {e}"
            return error_msg


def register_web_skills(registry) -> None:
    skills = [
        OpenURLSkill(),
        SearchSkill(),
        YouTubePlaySkill(),
        YouTubeMusicSkill(),
        WhatsAppPCSkill(),
        WhatsAppOpenSkill(),
        WeatherSkill(),
    ]
    
    for skill in skills:
        registry.register(skill.to_definition())