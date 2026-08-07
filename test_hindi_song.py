"""
Test ad skip with Hindi song - keeps browser open for manual verification.
Run: python test_hindi_song.py
"""

import asyncio
import sys
sys.path.insert(0, r'D:\Ansh Kesharwani\Documents\indus-phase1\indus')

from core.automation.playwright_automation import YouTubeAutomation, BrowserSession


async def test_hindi_song():
    """Test with a Hindi song and keep browser open."""
    # Hindi songs that typically have ads
    hindi_songs = [
        "armaan malik butta boma",
        "arijit singh tum hi ho",
        "arijit singh channa mereya",
        "atif aslam tera hone laga hoon",
        "neha kakkar mile ho tum humko",
        "jubin nautiyal raataan lambiyan",
        "sid sriram inkem inkem",
        "darshan raval bhula diya",
    ]
    
    song = hindi_songs[0]  # Pick first one
    print(f"Testing with Hindi song: {song}")
    
    # Use YouTubeAutomation directly with keep_open=True
    yt = YouTubeAutomation(browser_type="chromium")
    
    try:
        result = await yt.play_song(song, headless=False, keep_open=True)
        print(f"\nResult: {result}")
        
        # Keep browser open longer for manual verification
        print("\nBrowser will stay open for 60 seconds. Check if ad was skipped.")
        print("Watch the browser window - you should see:")
        print("1. Ad appears (if any)")
        print("2. Skip button appears after ~5 seconds")
        print("3. Ad gets skipped automatically")
        print("4. Video starts playing")
        await asyncio.sleep(60)
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Only close if keep_open didn't work
        await yt.session.close()


async def test_hindi_song_manual():
    """Manual test with detailed logging."""
    song = "arijit singh tum hi ho"
    print(f"Testing with: {song}")
    
    session = BrowserSession()
    
    try:
        await session.initialize(headless=False, browser_type="chromium")
        
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
        
        print("\nWaiting for ad (90s timeout)...")
        print("Watch the browser - you should see ad detection logs below:")
        
        ad_skipped = await session.wait_for_ad_skip(timeout=90000)
        
        is_playing = await session.evaluate("""
            () => {
                const video = document.querySelector('video');
                return video && !video.paused && video.currentTime > 0;
            }
        """)
        
        print(f"\nAd skipped: {ad_skipped}")
        print(f"Video playing: {is_playing}")
        
        # Keep open for manual check
        print("\nBrowser staying open for 60 seconds for manual verification...")
        await asyncio.sleep(60)
        
    finally:
        await session.close()


async def test_with_debug():
    """Test with debug output to see what skip buttons exist."""
    song = "arijit singh tum hi ho"
    print(f"Testing with DEBUG: {song}")
    
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
        
        print("\n=== DEBUG MODE: Monitoring for skip buttons every 2 seconds ===")
        print("Check console for 'Skip-related buttons found:' messages")
        
        # Custom wait with debug
        ad_skipped = False
        start_time = asyncio.get_event_loop().time()
        timeout_sec = 90
        
        while (asyncio.get_event_loop().time() - start_time) < timeout_sec:
            # Debug: log available skip-related elements
            debug_info = await session.page.evaluate("""
                () => {
                    const btns = document.querySelectorAll('button, [role="button"]');
                    const skipBtns = [];
                    for (const btn of btns) {
                        const aria = btn.getAttribute('aria-label') || '';
                        const text = btn.textContent || '';
                        const className = btn.className || '';
                        if ((aria.toLowerCase().includes('skip') || 
                             text.toLowerCase().includes('skip') ||
                             className.toLowerCase().includes('skip')) 
                            && btn.offsetParent !== null) {
                            skipBtns.push({
                                aria: aria,
                                text: text.trim().substring(0, 50),
                                class: className.substring(0, 100),
                                tag: btn.tagName,
                                visible: btn.offsetParent !== null
                            });
                        }
                    }
                    return skipBtns;
                }
            """)
            if debug_info:
                print(f"\n[DEBUG] Skip-related buttons found: {debug_info}")
            
            # Also check ad indicators
            ad_info = await session.page.evaluate("""
                () => {
                    const player = document.querySelector('.html5-video-player');
                    return {
                        hasAdCreated: player?.classList.contains('ad-created') || false,
                        className: player?.className || '',
                        videoAds: document.querySelector('.video-ads') !== null,
                        adModule: document.querySelector('.ytp-ad-module') !== null,
                    };
                }
            """)
            print(f"[DEBUG] Ad state: {ad_info}")
            
            # Try to click skip button
            skip_clicked = await session.page.evaluate("""
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
                print("[DEBUG] Skip button clicked!")
                ad_skipped = True
                break
            
            await asyncio.sleep(2)
        
        is_playing = await session.evaluate("""
            () => {
                const video = document.querySelector('video');
                return video && !video.paused && video.currentTime > 0;
            }
        """)
        
        print(f"\nFinal - Ad skipped: {ad_skipped}")
        print(f"Video playing: {is_playing}")
        
        print("\nBrowser staying open for 30 seconds for manual verification...")
        await asyncio.sleep(30)
        
    finally:
        await session.close()


if __name__ == "__main__":
    # Run the debug test
    asyncio.run(test_with_debug())