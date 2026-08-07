"""
Playwright-based browser automation for YouTube and WhatsApp Web.
Supports Chromium, Firefox, and WebKit (Safari).
"""

import asyncio
import random
from typing import Optional, Dict, Any, Literal
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

BrowserType = Literal["chromium", "firefox", "webkit"]

@dataclass
class BrowserSession:
    """Manages a Playwright browser session."""
    browser = None
    context = None
    page = None
    _playwright = None
    _initialized = False
    _browser_type: BrowserType = "chromium"
    _user_data_dir: str = None
    
    async def initialize(self, headless: bool = False, browser_type: BrowserType = "chromium", user_data_dir: str = None):
        """Initialize Playwright browser."""
        if self._initialized:
            return
            
        self._browser_type = browser_type
        self._user_data_dir = user_data_dir
        
        from playwright.async_api import async_playwright
        
        self._playwright = await async_playwright().start()
        
        # Launch appropriate browser
        if browser_type == "chromium":
            if user_data_dir:
                # Use persistent context for session persistence
                self.context = await self._playwright.chromium.launch_persistent_context(
                    user_data_dir=user_data_dir,
                    headless=headless,
                    viewport={"width": 1280, "height": 720},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-accelerated-2d-canvas",
                        "--no-first-run",
                        "--no-zygote",
                        "--disable-gpu",
                        "--disable-blink-features=AutomationControlled",
                    ]
                )
                self.browser = None  # Not used with persistent context
                self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()
            else:
                self.browser = await self._playwright.chromium.launch(
                    headless=headless,
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-accelerated-2d-canvas",
                        "--no-first-run",
                        "--no-zygote",
                        "--disable-gpu",
                        "--disable-blink-features=AutomationControlled",
                    ]
                )
                self.context = await self.browser.new_context(
                    viewport={"width": 1280, "height": 720},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                self.page = await self.context.new_page()
        elif browser_type == "firefox":
            self.browser = await self._playwright.firefox.launch(
                headless=headless,
            )
            self.context = await self.browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            self.page = await self.context.new_page()
        elif browser_type == "webkit":
            self.browser = await self._playwright.webkit.launch(
                headless=headless,
            )
            self.context = await self.browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            self.page = await self.context.new_page()
        else:
            raise ValueError(f"Unknown browser type: {browser_type}")
        
        self._initialized = True
        logger.info(f"Playwright {browser_type} browser initialized" + (" (persistent)" if user_data_dir else ""))
    
    async def close(self):
        """Close browser and cleanup."""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self._playwright:
            await self._playwright.stop()
        self._initialized = False
        logger.info("Playwright browser closed")
    
    async def navigate_and_wait(self, url: str, wait_until: str = "networkidle", timeout: int = 30000):
        """Navigate to URL and wait for load."""
        if not self._initialized:
            await self.initialize()
        await self.page.goto(url, wait_until=wait_until, timeout=timeout)
    
    async def click_selector(self, selector: str, timeout: int = 10000):
        """Click element by selector."""
        await self.page.wait_for_selector(selector, timeout=timeout)
        await self.page.click(selector)
    
    async def fill_input(self, selector: str, text: str, timeout: int = 10000):
        """Fill input field."""
        await self.page.wait_for_selector(selector, timeout=timeout)
        await self.page.fill(selector, text)
    
    async def wait_for_selector(self, selector: str, timeout: int = 10000):
        """Wait for element to appear."""
        await self.page.wait_for_selector(selector, timeout=timeout)
    
    async def evaluate(self, script: str):
        """Execute JavaScript in page context."""
        return await self.page.evaluate(script)
    
    async def screenshot(self, path: str):
        """Take screenshot."""
        await self.page.screenshot(path=path)
    
    async def wait_for_ad_skip(self, timeout: int = 30000) -> bool:
        """Wait for YouTube ad to be skippable and skip it immediately."""
        try:
            # Wait for ad indicators to appear (shorter initial wait)
            ad_indicators = [
                '.video-ads',
                '.ytp-ad-module',
                '.ytp-ad-player-overlay',
                '[class*="ad-showing"]',
            ]
            
            ad_found = False
            for indicator in ad_indicators:
                try:
                    await self.page.wait_for_selector(indicator, state='attached', timeout=2000)
                    logger.info(f"Ad detected via: {indicator}")
                    ad_found = True
                    break
                except:
                    continue
            
            if not ad_found:
                # Check for ad-created class on player
                has_ad_class = await self.page.evaluate("""
                    () => document.querySelector('.html5-video-player')?.classList.contains('ad-created')
                """)
                if has_ad_class:
                    logger.info("Ad detected via 'ad-created' class on player")
                    ad_found = True
            
            if not ad_found:
                logger.info("No ad detected")
                return False
            
            # Wait for skip button - check ALL buttons aggressively every 200ms
            # This is more reliable than specific selectors which change often
            start_time = asyncio.get_event_loop().time()
            timeout_sec = timeout / 1000
            
            while (asyncio.get_event_loop().time() - start_time) < timeout_sec:
                # Check via evaluate for ANY button with "skip" in aria-label, text, or class
                skip_clicked = await self.page.evaluate("""
                    () => {
                        const btns = document.querySelectorAll('button, [role="button"]');
                        for (const btn of btns) {
                            const aria = btn.getAttribute('aria-label') || '';
                            const text = btn.textContent || '';
                            const className = btn.className || '';
                            if ((aria.toLowerCase().includes('skip') || 
                                 text.toLowerCase().includes('skip') ||
                                 className.toLowerCase().includes('skip'))
                                && btn.offsetParent !== null) {
                                btn.click();
                                return true;
                            }
                        }
                        return false;
                    }
                """)
                if skip_clicked:
                    logger.info("Ad skipped immediately via evaluate (any skip button)")
                    await asyncio.sleep(0.5)
                    return True
                
                # Check every 200ms instead of 1s
                await asyncio.sleep(0.2)
            
            logger.info("Ad timeout or no skip button found (may be non-skippable)")
            return False
            
        except Exception as e:
            logger.info(f"No ad to skip or error: {e}")
            return False


class YouTubeAutomation:
    """Automate YouTube playback using Playwright."""
    
    def __init__(self, browser_type: BrowserType = "chromium"):
        self.session = BrowserSession()
        self.browser_type = browser_type
    
    async def play_song(self, query: str, headless: bool = False, keep_open: bool = False) -> Dict[str, Any]:
        """Search and play a song on YouTube.
        
        Args:
            query: Song search query
            headless: Run in headless mode
            keep_open: Keep browser open after playing (for manual verification)
        """
        try:
            await self.session.initialize(headless=headless, browser_type=self.browser_type)
            
            search_url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
            
            await self.session.navigate_and_wait(search_url)
            
            # Wait for video results
            await self.session.wait_for_selector("ytd-video-renderer", timeout=15000)
            
            # Click first video
            await self.session.click_selector("ytd-video-renderer:first-child #video-title")
            
            # Wait for video player to load
            await self.session.wait_for_selector(".html5-video-player", timeout=15000)
            
            # Wait for video ready
            await self.session.page.wait_for_function("""
                () => {
                    const video = document.querySelector('video');
                    return video && video.readyState >= 2;
                }
            """, timeout=15000)
            
            # Play video
            await self.session.evaluate("document.querySelector('video')?.play()")
            await asyncio.sleep(3)
            
            # Handle ads
            await self.session.wait_for_ad_skip()
            
            # Wait a moment for playback to start
            await asyncio.sleep(3)
            
            # Verify video is playing
            is_playing = await self.session.evaluate("""
                () => {
                    const video = document.querySelector('video');
                    return video && !video.paused && video.currentTime > 0;
                }
            """)
            
            return {
                "success": True,
                "playing": is_playing,
                "message": f"Playing song on YouTube ({self.browser_type})"
            }
            
        except Exception as e:
            logger.error(f"YouTube automation error: {e}")
            return {"success": False, "error": str(e)}
        finally:
            if not keep_open:
                await self.session.close()
    
    async def pause(self):
        """Pause video."""
        await self.session.evaluate("document.querySelector('video')?.pause()")
    
    async def play(self):
        """Resume video."""
        await self.session.evaluate("document.querySelector('video')?.play()")
    
    async def set_volume(self, volume: float):
        """Set volume (0.0 to 1.0)."""
        await self.session.evaluate(f"document.querySelector('video').volume = {volume}")


class WhatsAppWebAutomation:
    """Automate WhatsApp Web using Playwright."""
    
    def __init__(self, browser_type: BrowserType = "chromium", user_data_dir: str = None):
        self.session = BrowserSession()
        self._logged_in = False
        self.browser_type = browser_type
        self.user_data_dir = user_data_dir or r"D:\Ansh Kesharwani\Documents\indus-phase1\indus\whatsapp_session"
    
    async def initialize(self, headless: bool = False):
        """Initialize and check login status."""
        await self.session.initialize(headless=headless, browser_type=self.browser_type, user_data_dir=self.user_data_dir)
        
        # Go to WhatsApp Web
        await self.session.navigate_and_wait("https://web.whatsapp.com/")
        
        # Check if already logged in - try multiple selectors
        chat_list_selectors = [
            '[data-testid="chat-list"]',
            '[data-testid="chatlist"]',
            'div[aria-label="Chat list"]',
            '#pane-side',
        ]
        
        for selector in chat_list_selectors:
            try:
                await self.session.wait_for_selector(selector, timeout=3000)
                self._logged_in = True
                logger.info("WhatsApp Web already logged in")
                return
            except:
                continue
        
        # Wait for QR code
        qr_selectors = [
            '[data-ref]',
            'canvas[aria-label="Scan this QR code to link a device"]',
            'div[data-testid="qr-code"]',
        ]
        for selector in qr_selectors:
            try:
                await self.session.wait_for_selector(selector, timeout=5000)
                logger.info("WhatsApp Web requires QR code scan")
                self._logged_in = False
                return
            except:
                continue
        
        self._logged_in = False
    
    async def wait_for_login(self, timeout: int = 120000):
        """Wait for user to scan QR code."""
        if self._logged_in:
            return True
        
        chat_list_selectors = [
            '[data-testid="chat-list"]',
            '[data-testid="chatlist"]',
            'div[aria-label="Chat list"]',
            '#pane-side',
        ]
        
        start_time = asyncio.get_event_loop().time()
        while (asyncio.get_event_loop().time() - start_time) < (timeout / 1000):
            for selector in chat_list_selectors:
                try:
                    await self.session.wait_for_selector(selector, timeout=2000)
                    self._logged_in = True
                    logger.info("WhatsApp Web login successful")
                    return True
                except:
                    continue
            await asyncio.sleep(2)
        
        return False
    
    async def send_message(self, contact: str, message: str) -> Dict[str, Any]:
        """Send message to contact."""
        try:
            if not self._logged_in:
                await self.initialize()
                await self.wait_for_login()
            
            if not self._logged_in:
                return {"success": False, "error": "Not logged in to WhatsApp Web"}
            
            # Search for contact - try multiple selectors
            search_selectors = [
                '[data-testid="chat-list-search"]',
                '[data-testid="chatlist-search"]',
                'div[aria-label="Search input"]',
                'input[placeholder*="Search"]',
                'input[title*="Search"]',
            ]
            
            search_clicked = False
            for selector in search_selectors:
                try:
                    await self.session.click_selector(selector, timeout=3000)
                    search_clicked = True
                    break
                except:
                    continue
            
            if not search_clicked:
                return {"success": False, "error": "Could not find search box"}
            
            # Type contact name
            fill_selectors = [
                '[data-testid="chat-list-search"]',
                '[data-testid="chatlist-search"]',
                'div[aria-label="Search input"]',
                'input[placeholder*="Search"]',
            ]
            
            filled = False
            for selector in fill_selectors:
                try:
                    await self.session.fill_input(selector, contact)
                    filled = True
                    break
                except:
                    continue
            
            if not filled:
                return {"success": False, "error": "Could not type in search box"}
            
            await asyncio.sleep(2)
            
            # Click on contact
            try:
                await self.session.click_selector(f'span[title="{contact}"]', timeout=5000)
            except:
                # Try alternative
                try:
                    await self.session.click_selector(f'div[aria-label="{contact}"]', timeout=5000)
                except:
                    return {"success": False, "error": f"Could not find contact: {contact}"}
            
            await asyncio.sleep(1)
            
            # Type message - try multiple selectors
            msg_selectors = [
                '[data-testid="conversation-compose-box-input"]',
                '[data-testid="compose-box-input"]',
                'div[aria-label="Type a message"]',
                'footer div[contenteditable="true"]',
            ]
            
            msg_filled = False
            for selector in msg_selectors:
                try:
                    await self.session.fill_input(selector, message)
                    msg_filled = True
                    break
                except:
                    continue
            
            if not msg_filled:
                return {"success": False, "error": "Could not find message input"}
            
            await asyncio.sleep(0.5)
            
            # Send message - try multiple selectors
            send_selectors = [
                '[data-testid="compose-btn-send"]',
                '[data-testid="send-button"]',
                'button[aria-label="Send"]',
                'span[data-icon="send"]',
            ]
            
            sent = False
            for selector in send_selectors:
                try:
                    await self.session.click_selector(selector, timeout=3000)
                    sent = True
                    break
                except:
                    continue
            
            if not sent:
                return {"success": False, "error": "Could not find send button"}
            
            await asyncio.sleep(1)
            
            return {"success": True, "message": f"Sent message to {contact}"}
            
        except Exception as e:
            logger.error(f"WhatsApp automation error: {e}")
            return {"success": False, "error": str(e)}
    
    async def close(self):
        """Close browser."""
        await self.session.close()


# Global instances
_youtube_automation = None
_whatsapp_automation = None


def get_youtube_automation(browser_type: BrowserType = "chromium") -> YouTubeAutomation:
    global _youtube_automation
    if _youtube_automation is None:
        _youtube_automation = YouTubeAutomation(browser_type=browser_type)
    return _youtube_automation


def get_whatsapp_automation(browser_type: BrowserType = "chromium", user_data_dir: str = None) -> WhatsAppWebAutomation:
    global _whatsapp_automation
    if _whatsapp_automation is None:
        _whatsapp_automation = WhatsAppWebAutomation(browser_type=browser_type, user_data_dir=user_data_dir)
    return _whatsapp_automation


async def play_youtube_song(query: str, headless: bool = False, browser_type: BrowserType = "chromium", keep_open: bool = False) -> Dict[str, Any]:
    """Play a song on YouTube using browser automation."""
    yt = get_youtube_automation(browser_type=browser_type)
    return await yt.play_song(query, headless=headless, keep_open=keep_open)


async def send_whatsapp_message(contact: str, message: str) -> Dict[str, Any]:
    """Send WhatsApp message via Web automation."""
    wa = get_whatsapp_automation()
    return await wa.send_message(contact, message)


async def open_whatsapp_web() -> Dict[str, Any]:
    """Open WhatsApp Web and wait for login."""
    wa = get_whatsapp_automation()
    await wa.initialize()
    logged_in = await wa.wait_for_login(timeout=60000)
    return {"success": logged_in, "logged_in": logged_in}