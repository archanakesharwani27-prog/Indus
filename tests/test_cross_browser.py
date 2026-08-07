"""
Cross-browser YouTube ad skip verification test.
Run: python test_cross_browser.py
"""

import asyncio
import sys
sys.path.insert(0, r'D:\Ansh Kesharwani\Documents\indus-phase1\indus')

from core.automation.playwright_automation import BrowserSession, YouTubeAutomation


async def test_browser(browser_type: str, song: str, keep_open_seconds: int = 30):
    """Test ad skip on a specific browser."""
    print(f"\n{'='*60}")
    print(f"Testing {browser_type.upper()} with: {song}")
    print(f"{'='*60}")
    
    session = BrowserSession()
    
    try:
        await session.initialize(headless=False, browser_type=browser_type)
        
        search_url = f"https://www.youtube.com/results?search_query={song.replace(' ', '+')}"
        await session.navigate_and_wait(search_url)
        
        await session.wait_for_selector("ytd-video-renderer", timeout=15000)
        await session.click_selector("ytd-video-renderer:first-child #video-title")
        
        await session.wait_for_selector(".html5-video-player", timeout=15000)
        
        # Wait for video ready
        await session.page.wait_for_function("""
            () => {
                const video = document.querySelector('video');
                return video && video.readyState >= 2;
            }
        """, timeout=15000)
        
        await session.evaluate("document.querySelector('video')?.play()")
        await asyncio.sleep(3)
        
        print(f"Waiting for ad on {browser_type} (60s timeout)...")
        ad_skipped = await session.wait_for_ad_skip(timeout=60000)
        
        is_playing = await session.evaluate("""
            () => {
                const video = document.querySelector('video');
                return video && !video.paused && video.currentTime > 0;
            }
        """)
        
        print(f"\nResults for {browser_type}:")
        print(f"  Ad skipped: {ad_skipped}")
        print(f"  Video playing: {is_playing}")
        
        if keep_open_seconds > 0:
            print(f"\nBrowser staying open for {keep_open_seconds}s for manual verification...")
            await asyncio.sleep(keep_open_seconds)
        
        return {"browser": browser_type, "ad_skipped": ad_skipped, "playing": is_playing}
        
    except Exception as e:
        print(f"Error on {browser_type}: {e}")
        return {"browser": browser_type, "ad_skipped": False, "playing": False, "error": str(e)}
    finally:
        await session.close()


async def main():
    """Test ad skip across all supported browsers."""
    song = "rick astley never gonna give you up"
    
    # Test all three browsers
    browsers = ["chromium", "firefox", "webkit"]
    results = []
    
    for browser in browsers:
        try:
            result = await test_browser(browser, song, keep_open_seconds=20)
            results.append(result)
            await asyncio.sleep(3)  # Brief pause between browsers
        except Exception as e:
            print(f"Failed to test {browser}: {e}")
            results.append({"browser": browser, "ad_skipped": False, "playing": False, "error": str(e)})
    
    # Summary
    print(f"\n{'='*60}")
    print("CROSS-BROWSER TEST SUMMARY")
    print(f"{'='*60}")
    for r in results:
        status = "OK" if r.get("playing") else "FAIL"
        ad_status = "SKIPPED" if r.get("ad_skipped") else ("NO AD" if "error" not in r else f"ERROR: {r.get('error', 'unknown')[:40]}")
        print(f"  [{status}] {r['browser'].upper()}: Ad {ad_status}, Playing={r.get('playing', False)}")
    
    # Check which browsers work
    working = [r for r in results if r.get("playing")]
    print(f"\nWorking browsers: {len(working)}/{len(browsers)}")
    for r in working:
        print(f"  - {r['browser']} (ad_skipped={r['ad_skipped']})")


if __name__ == "__main__":
    asyncio.run(main())