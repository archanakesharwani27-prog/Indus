"""
Test ad skip on Edge with clear proof - multiple runs.
Run: python test_edge_proof.py
"""

import asyncio
import sys
sys.path.insert(0, r'D:\Ansh Kesharwani\Documents\indus-phase1\indus')

from core.automation.playwright_automation import BrowserSession


async def test_edge_proof():
    """Test on Edge with clear proof of skip click."""
    song = "arijit singh tum hi ho"
    print(f"Testing on EDGE with: {song}")
    print("=" * 60)
    
    from playwright.async_api import async_playwright
    playwright = await async_playwright().start()
    
    browser = await playwright.chromium.launch(
        headless=False,
        channel="msedge",
        args=[
            "--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage",
            "--disable-accelerated-2d-canvas", "--no-first-run", "--no-zygote",
            "--disable-gpu", "--disable-blink-features=AutomationControlled",
        ]
    )
    context = await browser.new_context(
        viewport={"width": 1280, "height": 720},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
    )
    page = await context.new_page()
    
    try:
        search_url = f"https://www.youtube.com/results?search_query={song.replace(' ', '+')}"
        await page.goto(search_url, wait_until="networkidle", timeout=30000)
        
        await page.wait_for_selector("ytd-video-renderer", timeout=15000)
        await page.click("ytd-video-renderer:first-child #video-title")
        
        await page.wait_for_selector(".html5-video-player", timeout=15000)
        
        await page.wait_for_function("""
            () => document.querySelector('video') && document.querySelector('video').readyState >= 2
        """, timeout=15000)
        
        await page.evaluate("document.querySelector('video')?.play()")
        await asyncio.sleep(3)
        
        print("\nMonitoring for ad and skip button...")
        print("-" * 60)
        
        # Test the ACTUAL wait_for_ad_skip method
        session = BrowserSession()
        session.page = page
        session.browser = browser
        session.context = context
        session._playwright = playwright
        session._initialized = True
        
        print("Calling session.wait_for_ad_skip()...")
        ad_skipped = await session.wait_for_ad_skip(timeout=60000)
        
        print(f"\nResult from wait_for_ad_skip(): {ad_skipped}")
        
        # Verify video is playing
        is_playing = await page.evaluate("""
            () => {
                const v = document.querySelector('video');
                return v && !v.paused && v.currentTime > 0;
            }
        """)
        print(f"Video playing: {is_playing}")
        
        if ad_skipped and is_playing:
            print("\n[PROOF] Ad skip WORKED - automation clicked the skip button!")
        else:
            print("\n[PROOF] Ad skip may not have worked")
        
        print("\nBrowser open for 20s manual check...")
        await asyncio.sleep(20)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await browser.close()
        await playwright.stop()


if __name__ == "__main__":
    asyncio.run(test_edge_proof())