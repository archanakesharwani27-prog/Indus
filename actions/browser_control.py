import asyncio
import threading
import concurrent.futures
import platform
import shutil
import subprocess
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout


def _get_default_browser_id() -> str:
    """Returns raw default browser identifier string for current OS."""
    system = platform.system()
    try:
        if system == "Windows":
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\http\UserChoice"
            )
            prog_id = winreg.QueryValueEx(key, "ProgId")[0].lower()
            winreg.CloseKey(key)
            return prog_id

        elif system == "Darwin":
            result = subprocess.run(
                ["defaults", "read",
                 "com.apple.LaunchServices/com.apple.launchservices.secure",
                 "LSHandlers"],
                capture_output=True, text=True, timeout=5
            )
            return result.stdout.lower()

        elif system == "Linux":
            result = subprocess.run(
                ["xdg-settings", "get", "default-web-browser"],
                capture_output=True, text=True, timeout=5
            )
            return result.stdout.lower()

    except Exception:
        pass

    return ""


_BROWSER_BINARIES = {
    "Windows": {
        "opera":   ["opera.exe"],
        "brave":   ["brave.exe"],
        "vivaldi": ["vivaldi.exe"],
        "chrome":  ["chrome.exe"],
        "firefox": ["firefox.exe"],
    },
    "Darwin": {
        "opera":   ["opera"],
        "brave":   ["brave browser", "brave"],
        "vivaldi": ["vivaldi"],
        "chrome":  ["google chrome", "google-chrome"],
        "firefox": ["firefox"],
    },
    "Linux": {
        "opera":   ["opera", "opera-stable"],
        "brave":   ["brave-browser", "brave"],
        "vivaldi": ["vivaldi-stable", "vivaldi"],
        "chrome":  ["google-chrome", "google-chrome-stable", "chromium-browser", "chromium"],
        "firefox": ["firefox"],
    },
}


def _get_opera_executable() -> str | None:
    if platform.system() != "Windows":
        return None
    try:
        import winreg
        candidate_keys = [
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\opera.exe",
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\launcher.exe",
            r"SOFTWARE\Clients\StartMenuInternet\OperaStable\shell\open\command",
            r"SOFTWARE\Clients\StartMenuInternet\OperaGXStable\shell\open\command",
        ]
        for key_path in candidate_keys:
            for hive in [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]:
                try:
                    key = winreg.OpenKey(hive, key_path)
                    val = winreg.QueryValue(key, None)
                    winreg.CloseKey(key)
                    exe = val.strip().strip('"').split('"')[0].split(" --")[0].strip()
                    if exe and Path(exe).exists():
                        print(f"[Browser] [SEARCH] Opera found via registry: {exe}")
                        return exe
                except Exception:
                    continue
    except Exception:
        pass
    return None


def _find_browser_executable(prog_id: str) -> tuple:
    """
    Returns (engine_name, exe_path, channel, is_opera).
    is_opera=True ? extra args needed to prevent private-mode launch.
    """
    system  = platform.system()
    os_bins = _BROWSER_BINARIES.get(system, {})

    if any(x in prog_id for x in ["firefox", "mozilla"]):
        return "firefox", None, None, False

    if "safari" in prog_id:
        return "webkit", None, None, False

    if "edge" in prog_id:
        return "chromium", None, "msedge", False

    if "opera" in prog_id:
        exe = _get_opera_executable()
        if exe:
            return "chromium", exe, None, True
        for binary in os_bins.get("opera", []):
            path = shutil.which(binary)
            if path:
                return "chromium", path, None, True

    browser_patterns = {
        "brave":   ["brave"],
        "vivaldi": ["vivaldi"],
        "chrome":  ["chrome"],
    }
    for browser_name, patterns in browser_patterns.items():
        if not any(p in prog_id for p in patterns):
            continue
        binaries = os_bins.get(browser_name, [])
        for binary in binaries:
            path = shutil.which(binary)
            if path:
                print(f"[Browser] [SEARCH] Found {browser_name} at: {path}")
                return "chromium", path, None, False

    if "chrome" in prog_id or not prog_id:
        return "chromium", None, "chrome", False

    return "chromium", None, None, False


class _BrowserThread:

    def __init__(self):
        self._loop       = None
        self._thread     = None
        self._ready      = threading.Event()
        self._playwright = None
        self._browser    = None
        self._context    = None
        self._page       = None
        self._engine_name = "chromium"
        self._exe_path   = None
        self._channel    = None
        self._is_opera   = False

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(
            target=self._run_loop, daemon=True, name="BrowserThread"
        )
        self._thread.start()
        self._ready.wait(timeout=15)

    def _run_loop(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._init())
        self._ready.set()
        self._loop.run_forever()

    async def _init(self):
        self._playwright = await async_playwright().start()

    def run(self, coro, timeout: int = 30):
        if not self._loop:
            raise RuntimeError("BrowserThread not started.")
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=timeout)

    # -- Taray?c? ve sayfa yönetimi -------------------------------------------

    async def _launch_browser_if_needed(self):
        """
        Taray?c?y? ba?lat?r. Zaten aç?ksa hiçbir ?ey yapmaz.
        Her zaman default taray?c?y? kullan?r, özel sekme açmaz.
        """
        if self._browser and self._browser.is_connected():
            return

        prog_id = _get_default_browser_id()
        self._engine_name, self._exe_path, self._channel, self._is_opera = _find_browser_executable(prog_id)
        engine = getattr(self._playwright, self._engine_name)

        # Temel chromium argümanlar?
        chromium_args = ["--start-maximized"]

        if self._is_opera:
            # Opera GX baz? sürümlerde varsay?lan olarak private modda ba?lar.
            # A?a??daki flag'ler bunu engeller.
            chromium_args += [
                "--disable-features=OperaPrivacyMode",
                "--no-private",
            ]
            print("[Browser] ? Opera detected -- disabling private-mode flags")

        launch_kwargs = {"headless": False}
        if self._engine_name == "chromium":
            launch_kwargs["args"] = chromium_args
        if self._exe_path:
            launch_kwargs["executable_path"] = self._exe_path
        elif self._channel:
            launch_kwargs["channel"] = self._channel

        try:
            self._browser = await engine.launch(**launch_kwargs)
            print(
                f"[Browser] [OK] Launched ({self._engine_name}"
                f"{' / ' + self._channel if self._channel else ''}"
                f"{' / ' + self._exe_path if self._exe_path else ''})"
            )
        except Exception as e:
            print(f"[Browser] [WARN] Launch failed ({e}), falling back to built-in Chromium")
            self._browser = await self._playwright.chromium.launch(
                headless=False,
                args=["--start-maximized"]
            )

    async def _get_page(self):
        """
        Mevcut sayfay? döndürür.
        - Taray?c? kapal?ysa açar.
        - Context yoksa olu?turur.
        - Sayfa kapal?ysa yeni sekme açar (ayn? pencerede).
        - Sayfa zaten aç?ksa ayn? sayfay? döndürür (yeni pencere açmaz).
        """
        await self._launch_browser_if_needed()

        if self._context is None:
            self._context = await self._browser.new_context(
                viewport=None,
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            )

        if self._page is None or self._page.is_closed():
            self._page = await self._context.new_page()

        return self._page

    # -- Eylemler -------------------------------------------------------------

    async def _go_to(self, url: str) -> str:
        if not url.startswith("http"):
            url = "https://" + url
        page = await self._get_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            return f"Opened: {page.url}"
        except PlaywrightTimeout:
            return f"Timeout loading: {url}"
        except Exception as e:
            return f"Navigation error: {e}"

    async def _search(self, query: str, engine: str = "google") -> str:
        engines = {
            "google":     f"https://www.google.com/search?q={query.replace(' ', '+')}",
            "bing":       f"https://www.bing.com/search?q={query.replace(' ', '+')}",
            "duckduckgo": f"https://duckduckgo.com/?q={query.replace(' ', '+')}",
        }
        url = engines.get(engine.lower(), engines["google"])
        return await self._go_to(url)

    async def _click(self, selector=None, text=None) -> str:
        page = await self._get_page()
        try:
            if text:
                await page.get_by_text(text, exact=False).first.click(timeout=8000)
                return f"Clicked: '{text}'"
            elif selector:
                await page.click(selector, timeout=8000)
                return f"Clicked: {selector}"
            return "No selector or text provided."
        except PlaywrightTimeout:
            return "Element not found or not clickable."
        except Exception as e:
            return f"Click error: {e}"

    async def _type(self, selector=None, text: str = "", clear_first: bool = True) -> str:
        page = await self._get_page()
        try:
            element = page.locator(selector).first if selector else page.locator(":focus")
            if clear_first:
                await element.clear()
            await element.type(text, delay=50)
            return "Text typed."
        except Exception as e:
            return f"Type error: {e}"

    async def _scroll(self, direction: str = "down", amount: int = 500) -> str:
        page = await self._get_page()
        try:
            y = amount if direction == "down" else -amount
            await page.mouse.wheel(0, y)
            return f"Scrolled {direction}."
        except Exception as e:
            return f"Scroll error: {e}"

    async def _press(self, key: str) -> str:
        page = await self._get_page()
        try:
            await page.keyboard.press(key)
            return f"Pressed: {key}"
        except Exception as e:
            return f"Key error: {e}"

    async def _get_text(self) -> str:
        page = await self._get_page()
        try:
            text = await page.inner_text("body")
            return text[:4000] if len(text) > 4000 else text
        except Exception as e:
            return f"Could not get page text: {e}"

    async def _fill_form(self, fields: dict) -> str:
        page    = await self._get_page()
        results = []
        for selector, value in fields.items():
            try:
                el = page.locator(selector).first
                await el.clear()
                await el.type(str(value), delay=40)
                results.append(f"[OK] {selector}")
            except Exception as e:
                results.append(f"? {selector}: {e}")
        return "Form filled: " + ", ".join(results)

    async def _smart_click(self, description: str) -> str:
        page       = await self._get_page()
        desc_lower = description.lower()

        role_hints = {
            "button":    ["button", "buton", "btn"],
            "link":      ["link", "ba?lant?"],
            "searchbox": ["search", "arama"],
            "textbox":   ["input", "field", "alan"],
        }
        for role, keywords in role_hints.items():
            if any(k in desc_lower for k in keywords):
                try:
                    await page.get_by_role(role).first.click(timeout=5000)
                    return f"Clicked ({role}): '{description}'"
                except Exception:
                    pass

        try:
            await page.get_by_text(description, exact=False).first.click(timeout=5000)
            return f"Clicked (text): '{description}'"
        except Exception:
            pass

        try:
            await page.get_by_placeholder(description, exact=False).first.click(timeout=5000)
            return f"Clicked (placeholder): '{description}'"
        except Exception:
            pass

        return f"Could not find: '{description}'"

    async def _smart_type(self, description: str, text: str) -> str:
        page = await self._get_page()

        for method, locator in [
            ("placeholder", page.get_by_placeholder(description, exact=False)),
            ("label",       page.get_by_label(description, exact=False)),
            ("role",        page.get_by_role("textbox")),
        ]:
            try:
                el = locator.first
                await el.clear()
                await el.type(text, delay=50)
                return f"Typed into ({method}): '{description}'"
            except Exception:
                continue

        return f"Could not find input: '{description}'"

    async def _close_browser(self) -> str:
        if self._browser:
            await self._browser.close()
            self._browser = None
            self._context = None
            self._page    = None

        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

        return "Browser closed."

    async def _skip_youtube_ad(self) -> str:
        """Wait for a YouTube ad and skip it as soon as the skip button appears."""
        page = await self._get_page()
        try:
            # Wait up to 35 seconds for the skip button to appear
            skip_selectors = [
                ".ytp-skip-ad-button",
                ".ytp-ad-skip-button",
                "button.ytp-skip-ad-button",
                "[class*='skip-ad']",
                ".ytp-ad-skip-button-modern",
            ]
            for attempt in range(35):
                for sel in skip_selectors:
                    try:
                        btn = page.locator(sel).first
                        if await btn.is_visible(timeout=1000):
                            await btn.click()
                            return "Ad skipped successfully."
                    except Exception:
                        pass
                # Also try clicking by text
                for txt in ["Skip Ad", "Skip Ads", "Skip", "???????? ??????", "Reklam? Geç"]:
                    try:
                        btn = page.get_by_text(txt, exact=False).first
                        if await btn.is_visible(timeout=500):
                            await btn.click()
                            return f"Ad skipped (text: '{txt}')."
                    except Exception:
                        pass
                await asyncio.sleep(1)
            return "No skippable ad found within 35 seconds."
        except Exception as e:
            return f"Skip ad error: {e}"

    async def _wait_for_element(self, selector: str = None, text: str = None, timeout: int = 30) -> str:
        """Wait for an element to appear on the page."""
        page = await self._get_page()
        try:
            if text:
                await page.get_by_text(text, exact=False).first.wait_for(
                    state="visible", timeout=timeout * 1000
                )
                return f"Element '{text}' appeared."
            elif selector:
                await page.locator(selector).first.wait_for(
                    state="visible", timeout=timeout * 1000
                )
                return f"Element '{selector}' appeared."
            return "No selector or text provided."
        except PlaywrightTimeout:
            return f"Timed out waiting for element after {timeout}s."
        except Exception as e:
            return f"Wait error: {e}"

    async def _stream_play(self, site: str, query: str, confirm: bool = False) -> str:
        """
        Navigate to a streaming site and search + click the best match.
        Supports: sony_liv, netflix, hotstar, prime, netmirror, jiocinema, zee5, youtube.
        """
        site = site.lower().strip()
        site_map = {
            "sony_liv":   ("https://www.sonyliv.com", f"https://www.sonyliv.com/search?keyword={query.replace(' ', '+')}"),
            "sonyliv":    ("https://www.sonyliv.com", f"https://www.sonyliv.com/search?keyword={query.replace(' ', '+')}"),
            "hotstar":    ("https://www.hotstar.com",  f"https://www.hotstar.com/in/search?q={query.replace(' ', '+')}"),
            "disney":     ("https://www.hotstar.com",  f"https://www.hotstar.com/in/search?q={query.replace(' ', '+')}"),
            "prime":      ("https://www.primevideo.com", f"https://www.primevideo.com/search/?phrase={query.replace(' ', '+')}"),
            "amazon":     ("https://www.primevideo.com", f"https://www.primevideo.com/search/?phrase={query.replace(' ', '+')}"),
            "netflix":    ("https://www.netflix.com",  f"https://www.netflix.com/search?q={query.replace(' ', '+')}"),
            "netmirror":  ("https://www.netmirror.app", f"https://www.netmirror.app/search/{query.replace(' ', '-')}"),
            "jiocinema":  ("https://www.jiocinema.com", f"https://www.jiocinema.com/search/{query.replace(' ', '%20')}"),
            "zee5":       ("https://www.zee5.com", f"https://www.zee5.com/search?q={query.replace(' ', '+')}"),
            "youtube":    ("https://www.youtube.com",  f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"),
        }

        if site not in site_map:
            # Try generic: go to site URL and search
            base = f"https://www.{site}.com"
            search_url = f"{base}/search?q={query.replace(' ', '+')}"
        else:
            base, search_url = site_map[site]

        page = await self._get_page()

        # Navigate to search results
        await page.goto(search_url, wait_until="domcontentloaded", timeout=20000)
        await asyncio.sleep(2)

        # Try to click the first result that matches query keywords
        query_words = [w for w in query.lower().split() if len(w) > 2]
        clicked = False

        # Common result selectors for streaming sites
        result_selectors = [
            "a[href*='episode']", "a[href*='watch']", "a[href*='play']",
            ".title", ".content-title", ".card-title", ".show-title",
            "[class*='title']", "[class*='card']", "[class*='result']",
            "article a", ".thumbnail a", "h3 a", "h2 a",
        ]

        for sel in result_selectors:
            try:
                items = page.locator(sel)
                count = await items.count()
                for i in range(min(count, 10)):
                    item = items.nth(i)
                    try:
                        txt = (await item.inner_text(timeout=2000)).lower()
                        if any(word in txt for word in query_words):
                            await item.click(timeout=5000)
                            clicked = True
                            break
                    except Exception:
                        continue
                if clicked:
                    break
            except Exception:
                continue

        if not clicked:
            # If specific query keywords did not match a clickable item, do NOT blindly click a.first
            # (which causes clicking hero banners / logos like KBC on SonyLIV).
            print(f"[Browser] ?? Exact result card not auto-clicked for '{query}', waiting on search page.")
            return f"Navigated to search results for '{query}' on {site}. URL: {page.url}"

        await asyncio.sleep(2)

        # Try to find and click a Play button
        play_selectors = [
            "button[aria-label*='play' i]", "button[aria-label*='Play' i]",
            "[class*='play-btn']", "[class*='play_btn']", "[class*='playBtn']",
            "[class*='play-button']", ".play-icon", "#play-button",
            "button[title*='Play' i]", "[data-testid*='play' i]",
        ]
        for sel in play_selectors:
            try:
                btn = page.locator(sel).first
                if await btn.is_visible(timeout=3000):
                    await btn.click()
                    return f"Playing '{query}' on {site}. Playback started."
            except Exception:
                continue

        # Try clicking by text for play buttons
        for play_text in ["Play", "Watch Now", "?", "Play Now", "Watch", "Resume"]:
            try:
                btn = page.get_by_text(play_text, exact=False).first
                if await btn.is_visible(timeout=2000):
                    await btn.click()
                    return f"Playing '{query}' on {site}."
            except Exception:
                continue

        current_url = page.url
        return f"Navigated to '{query}' on {site}. URL: {current_url}. Please click Play if not auto-started."

    async def _get_page_title(self) -> str:
        page = await self._get_page()
        try:
            return await page.title()
        except Exception as e:
            return f"Could not get title: {e}"


# -- Singleton browser thread -------------------------------------------------

_bt         = _BrowserThread()
_bt_started = False
_bt_lock    = threading.Lock()


def _ensure_started():
    global _bt_started
    with _bt_lock:
        if not _bt_started:
            _bt.start()
            _bt_started = True


# -- Public API ---------------------------------------------------------------

def browser_control(
    parameters:     dict,
    response=None,
    player=None,
    session_memory=None
) -> str:
    """
    Browser controller -- auto-detects and uses system default browser.
    Always reuses the existing browser window/page; never opens incognito.

    parameters:
        action      : go_to | search | click | type | scroll | fill_form |
                      smart_click | smart_type | get_text | press | close
        url         : URL for go_to
        query       : search query
        engine      : google | bing | duckduckgo (default: google)
        selector    : CSS selector for click/type
        text        : text to click or type
        description : element description for smart_click/smart_type
        direction   : up | down for scroll
        amount      : scroll amount in pixels (default: 500)
        key         : key name for press (e.g. Enter, Escape, Tab)
        fields      : {selector: value} dict for fill_form
        clear_first : bool, clear input before typing (default: True)
    """
    _ensure_started()

    action = (parameters or {}).get("action", "").lower().strip()
    result = "Unknown action."

    try:
        if action == "go_to":
            url = parameters.get("url", "")
            force_playwright = parameters.get("force_playwright", False)

            if url and not force_playwright:
                # Always open in system default browser first (avoids Playwright bot detection)
                import webbrowser as _wb
                import time as _t
                _wb.open(url)
                _t.sleep(0.5)
                result = f"Opened in system browser: {url}"
            else:
                result = _bt.run(_bt._go_to(url))

        elif action == "search":
            result = _bt.run(_bt._search(
                parameters.get("query", ""),
                parameters.get("engine", "google"),
            ))

        elif action == "click":
            result = _bt.run(_bt._click(
                selector=parameters.get("selector"),
                text=parameters.get("text"),
            ))

        elif action == "type":
            result = _bt.run(_bt._type(
                selector=parameters.get("selector"),
                text=parameters.get("text", ""),
                clear_first=parameters.get("clear_first", True),
            ))

        elif action == "scroll":
            result = _bt.run(_bt._scroll(
                direction=parameters.get("direction", "down"),
                amount=parameters.get("amount", 500),
            ))

        elif action == "fill_form":
            result = _bt.run(_bt._fill_form(parameters.get("fields", {})))

        elif action == "smart_click":
            result = _bt.run(_bt._smart_click(parameters.get("description", "")))

        elif action == "smart_type":
            result = _bt.run(_bt._smart_type(
                parameters.get("description", ""),
                parameters.get("text", ""),
            ))

        elif action == "get_text":
            result = _bt.run(_bt._get_text())

        elif action == "press":
            result = _bt.run(_bt._press(parameters.get("key", "Enter")))

        elif action == "close":
            result = _bt.run(_bt._close_browser())

        elif action == "skip_ad":
            from actions.universal_ad_skipper import universal_ad_skipper
            result = universal_ad_skipper(parameters={"action": "skip_ad"}, player=player)

        elif action == "wait_for_element":
            result = _bt.run(_bt._wait_for_element(
                selector=parameters.get("selector"),
                text=parameters.get("text"),
                timeout=parameters.get("timeout", 30),
            ), timeout=parameters.get("timeout", 30) + 5)

        elif action == "stream_play":
            result = _bt.run(_bt._stream_play(
                site=parameters.get("site", ""),
                query=parameters.get("query", ""),
            ), timeout=60)

        elif action == "get_title":
            result = _bt.run(_bt._get_page_title())

        else:
            result = f"Unknown action: {action}"

    except concurrent.futures.TimeoutError:
        result = "Browser action timed out."
    except Exception as e:
        result = f"Browser error: {e}"

    safe_res = result[:80].encode("ascii", errors="replace").decode("ascii")
    print(f"[Browser] {safe_res}")
    if player:
        player.write_log(f"[browser] {safe_res[:60]}")

    return result