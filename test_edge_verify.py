"""
Test ad skip on Microsoft Edge browser with detailed verification.
Run: python test_edge_verify.py
"""

import asyncio
import sys
sys.path.insert(0, r'D:\Ansh Kesharwani\Documents\indus-phase1\indus')

from core.automation.playwright_automation import BrowserSession


async def test_edge_with_verification():
    """Test on Edge with detailed logging to verify ad skip actually happened."""
    song = "arijit singh tum hi ho"
    print(f"Testing on EDGE with: {song}")
    print("=" * 60)
    
    session = BrowserSession()
    
    try:
        # Use Edge via Chromium channel
        from playwright.async_api import async_playwright
        playwright = await async_playwright().start()
        
        # Launch Edge specifically
        browser = await playwright.chromium.launch(
            headless=False,
            channel="msedge",  # This launches Microsoft Edge
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
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
        )
        page = await context.new_page()
        
        # Set session page to our Edge page
        session.page = page
        session.browser = browser
        session.context = context
        session._playwright = playwright
        session._initialized = True
        
        search_url = f"https://www.youtube.com/results?search_query={song.replace(' ', '+')}"
        await page.goto(search_url, wait_until="networkidle", timeout=30000)
        
        await page.wait_for_selector("ytd-video-renderer", timeout=15000)
        await page.click("ytd-video-renderer:first-child #video-title")
        
        await page.wait_for_selector(".html5-video-player", timeout=15000)
        
        await page.wait_for_function("""
            () => {
                const video = document.querySelector('video');
                return video && video.readyState >= 2;
            }
        """, timeout=15000)
        
        await page.evaluate("document.querySelector('video')?.play()")
        await asyncio.sleep(3)
        
        print("\n[VERIFICATION] Video started, now monitoring for ad...")
        print("[VERIFICATION] Checking ad state every 2 seconds")
        print("-" * 60)
        
        # Monitor ad state with detailed logging
        ad_skipped = False
        start_time = asyncio.get_event_loop().time()
        timeout_sec = 90
        
        while (asyncio.get_event_loop().time() - start_time) < timeout_sec:
            # Get detailed ad state
            ad_state = await page.evaluate("""
                () => {
                    const player = document.querySelector('.html5-video-player');
                    const video = document.querySelector('video');
                    
                    // Check for skip button
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
                                visible: true
                            });
                        }
                    }
                    
                    return {
                        playerClass: player?.className || '',
                        hasAdCreated: player?.classList.contains('ad-created') || false,
                        hasAdShowing: player?.classList.contains('ad-showing') || false,
                        hasAdInterrupting: player?.classList.contains('ad-interrupting') || false,
                        videoPaused: video?.paused,
                        videoCurrentTime: video?.currentTime || 0,
                        skipButtons: skipBtns,
                        videoAds: document.querySelector('.video-ads') !== null,
                        adModule: document.querySelector('.ytp-ad-module') !== null,
                    };
                }
            """)
            
            elapsed = int(asyncio.get_event_loop().time() - start_time)
            print(f"[{elapsed:2d}s] AdCreated: {ad_state['hasAdCreated']}, AdShowing: {ad_state['hasAdShowing']}, AdInterrupting: {ad_state['hasAdInterrupting']}")
            print(f"       VideoPaused: {ad_state['videoPaused']}, CurrentTime: {ad_state['videoCurrentTime']:.1f}s")
            print(f"       SkipButtons: {ad_state['skipButtons']}")
            
            if ad_state['skipButtons']:
                print(f"       >>> SKIP BUTTON FOUND! Clicking...")
                # Click the skip button
                for btn_info in ad_state['skipButtons']:
                    # Try to find and click via evaluate
                    clicked = await page.evaluate("""
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
                    if clicked:
                        print(f"       >>> SKIP BUTTON CLICKED!")
                        ad_skipped = True
                        break
                if ad_skipped:
                    break
            
            # Also check if video is playing (ad might have finished)
            if ad_state['videoCurrentTime'] > 5 and not ad_state['videoPaused']:
                print(f"       >>> Video playing normally (no ad or ad finished)")
                break
                
            await asyncio.sleep(2)
        
        # Final verification
        final_state = await page.evaluate("""
            () => {
                const video = document.querySelector('video');
                const player = document.querySelector('.html5-video-player');
                return {
                    playing: video && !video.paused && video.currentTime > 0,
                    currentTime: video?.currentTime || 0,
                    paused: video?.paused,
                    playerClass: player?.className || '',
                };
            }
        """)
        
        print("-" * 60)
        print(f"[FINAL VERIFICATION]")
        print(f"  Ad Skipped by automation: {ad_skipped}")
        print(f"  Video Playing: {final_state['playing']}")
        print(f"  Current Time: {final_state['currentTime']:.1f}s")
        print(f"  Player Classes: {final_state['playerClass'][:100]}...")
        
        if final_state['playing'] and final_state['currentTime'] > 0:
            print(f"\n  [SUCCESS] Video is playing on Microsoft Edge!")
        else:
            print(f"\n  [FAILED] Video not playing properly")
        
        print(f"\nBrowser staying open for 30 seconds for manual verification...")
        await asyncio.sleep(30)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            await session.close()
        except:
            pass


if __name__ == "__main__":
    asyncio.run(test_edge_with_verification())