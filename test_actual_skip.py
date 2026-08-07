"""
Test ad skip with Hindi song using the actual wait_for_ad_skip method.
Run: python test_actual_skip.py
"""

import asyncio
import sys
sys.path.insert(0, r'D:\Ansh Kesharwani\Documents\indus-phase1\indus')

from core.automation.playwright_automation import BrowserSession


async def test_actual_skip():
    """Test using the actual wait_for_ad_skip method."""
    song = "arijit singh tum hi ho"
    print(f"Testing actual wait_for_ad_skip with: {song}")
    
    session = BrowserSession()
    
    try:
        await session.initialize(headless=False, browser_type="chromium")
        
        search_url = f"https://www.youtube.com/results?search_query={song.replace(' ', '+')}"
        await session.navigate_and_wait(search_url)
        
        await session.wait_for_selector("ytd-video-renderer", timeout=15000)
        await session.click_selector("ytd-video-renderer:first-child #video-title")
        
        await session.wait_for_selector(".html5-video-player", timeout=15000)
        
        await session.page.wait_for_function("""
            () => {
                const video = document.querySelector('video');
                return video && video.readyState >= 2;
            }
        """, timeout=15000)
        
        await session.evaluate("document.querySelector('video')?.play()")
        await asyncio.sleep(3)
        
        print("\nCalling wait_for_ad_skip (60s timeout)...")
        
        ad_skipped = await session.wait_for_ad_skip(timeout=60000)
        
        is_playing = await session.evaluate("""
            () => {
                const video = document.querySelector('video');
                return video && !video.paused && video.currentTime > 0;
            }
        """)
        
        print(f"\nResult - Ad skipped: {ad_skipped}")
        print(f"Video playing: {is_playing}")
        
        print("\nBrowser staying open for 30 seconds for manual verification...")
        await asyncio.sleep(30)
        
    finally:
        await session.close()


if __name__ == "__main__":
    asyncio.run(test_actual_skip())