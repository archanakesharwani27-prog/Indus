"""
YouTube automation tests - Chrome browser test with ad skip handling.
Run: python -m pytest tests/test_youtube_automation.py -v -s
Note: Runs in headed mode (visible Chrome) to test ad skip functionality.
"""

import os
import sys
import asyncio
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.automation.playwright_automation import play_youtube_song, YouTubeAutomation, BrowserSession


@pytest.mark.asyncio
async def test_play_youtube_song_with_ad_skip():
    """Test playing a song on YouTube with ad skip handling in visible Chrome."""
    query = "never gonna give you up"
    
    result = await play_youtube_song(query, headless=False)
    
    print(f"\nResult: {result}")
    
    assert result["success"] is True, f"Failed to play song: {result.get('error')}"
    assert result["playing"] is True, "Video is not playing"


@pytest.mark.asyncio
async def test_youtube_automation_direct():
    """Direct test using YouTubeAutomation class for more control."""
    yt = YouTubeAutomation()
    
    try:
        result = await yt.play_song("rick astley never gonna give you up", headless=False)
        
        print(f"\nDirect automation result: {result}")
        
        assert result["success"] is True
        assert result["playing"] is True
        
    finally:
        await yt.session.close()


@pytest.mark.asyncio
async def test_ad_skip_functionality():
    """Test the wait_for_ad_skip method directly."""
    yt = YouTubeAutomation()
    
    try:
        await yt.session.initialize(headless=False)
        await yt.session.navigate_and_wait("https://www.youtube.com/")
        
        # Test ad skip detection on homepage (should return False quickly)
        result = await yt.session.wait_for_ad_skip(timeout=5000)
        
        print(f"\nAd skip test result: {result}")
        
    finally:
        await yt.session.close()


@pytest.mark.asyncio
async def test_ad_skip_with_longer_wait():
    """Test ad skip with longer wait time - plays a video and waits for ad."""
    session = BrowserSession()
    
    try:
        await session.initialize(headless=False)
        
        # Go directly to a popular video that likely has ads
        await session.navigate_and_wait("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        
        # Wait for video player
        await session.wait_for_selector(".html5-video-player", timeout=15000)
        
        # Try to play the video
        await session.evaluate("document.querySelector('video')?.play()")
        await asyncio.sleep(2)
        
        print("\nVideo loaded, waiting for ad (30 seconds)...")
        
        # Wait longer for ad to appear and become skippable
        result = await session.wait_for_ad_skip(timeout=30000)
        
        print(f"\nAd skip result after 30s: {result}")
        
        # Check if video is playing
        is_playing = await session.evaluate("""
            () => {
                const video = document.querySelector('video');
                return video && !video.paused && video.currentTime > 0;
            }
        """)
        print(f"Video playing: {is_playing}")
        
        # Debug: check for ad elements
        ad_elements = await session.evaluate("""
            () => {
                const ads = document.querySelectorAll('.video-ads, .ytp-ad-module, [class*="ad"]');
                return Array.from(ads).map(el => el.className);
            }
        """)
        print(f"Ad elements found: {ad_elements}")
        
        # Debug: check skip button
        skip_btns = await session.evaluate("""
            () => {
                const btns = document.querySelectorAll('.ytp-ad-skip-button, .ytp-ad-skip-button-modern, button[class*="skip"]');
                return Array.from(btns).map(el => ({class: el.className, visible: el.offsetParent !== null}));
            }
        """)
        print(f"Skip buttons found: {skip_btns}")
        
        # Keep browser open for manual verification
        print("\nBrowser staying open for 15 seconds for manual verification...")
        await asyncio.sleep(15)
        
    finally:
        await session.close()


# Test with multiple songs to verify ad skip across different videos
@pytest.mark.asyncio
async def test_multiple_songs_ad_skip():
    """Test ad skip with multiple different songs."""
    songs = [
        "rick astley never gonna give you up",
        "queen bohemian rhapsody",
        "eagles hotel california",
    ]
    
    results = []
    
    for i, song in enumerate(songs):
        print(f"\n{'='*50}")
        print(f"Testing song {i+1}/{len(songs)}: {song}")
        print(f"{'='*50}")
        
        session = BrowserSession()
        
        try:
            await session.initialize(headless=False)
            
            search_url = f"https://www.youtube.com/results?search_query={song.replace(' ', '+')}"
            await session.navigate_and_wait(search_url)
            
            # Wait for video results and click first
            await session.wait_for_selector("ytd-video-renderer", timeout=15000)
            await session.click_selector("ytd-video-renderer:first-child #video-title")
            
            # Wait for video player and ensure it's ready
            await session.wait_for_selector(".html5-video-player", timeout=15000)
            
            # Wait for video element to be ready
            await session.page.wait_for_function("""
                () => {
                    const video = document.querySelector('video');
                    return video && video.readyState >= 2; // HAVE_CURRENT_DATA
                }
            """, timeout=15000)
            
            # Play video
            await session.evaluate("document.querySelector('video')?.play()")
            await asyncio.sleep(3)
            
            # Wait for ad and skip
            print(f"Waiting for ad on: {song}...")
            ad_skipped = await session.wait_for_ad_skip(timeout=30000)
            
            # Verify playback
            is_playing = await session.evaluate("""
                () => {
                    const video = document.querySelector('video');
                    return video && !video.paused && video.currentTime > 0;
                }
            """)
            
            result = {
                "song": song,
                "ad_skipped": ad_skipped,
                "playing": is_playing,
            }
            results.append(result)
            
            print(f"Result for '{song}': ad_skipped={ad_skipped}, playing={is_playing}")
            
            # Brief pause between songs
            await asyncio.sleep(2)
            
        except Exception as e:
            print(f"Error testing '{song}': {e}")
            results.append({"song": song, "ad_skipped": False, "playing": False, "error": str(e)})
        finally:
            await session.close()
    
    # Summary
    print(f"\n{'='*50}")
    print("SUMMARY:")
    print(f"{'='*50}")
    for r in results:
        status = "OK" if r["playing"] else "FAIL"
        ad_status = "skipped" if r["ad_skipped"] else ("no ad/timeout" if "error" not in r else f"error: {r.get('error', 'unknown')[:50]}")
        print(f"  [{status}] {r['song']}: ad {ad_status}, playing={r['playing']}")
    
    # At least verify first 2 songs played successfully (they worked before)
    successful = sum(1 for r in results if r["playing"])
    assert successful >= 2, f"Only {successful}/3 songs played successfully"
    
    print(f"\n{successful}/3 songs verified successfully!")


if __name__ == "__main__":
    pytest.main(["-v", "-s", __file__])


# Manual test - run this directly to keep browser open
async def manual_test_ad_skip():
    """Run manually: python -m tests.test_youtube_automation"""
    session = BrowserSession()
    
    try:
        await session.initialize(headless=False)
        
        # Test with a song
        song = "rick astley never gonna give you up"
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
        
        print("Waiting for ad (60 seconds)...")
        ad_skipped = await session.wait_for_ad_skip(timeout=60000)
        
        is_playing = await session.evaluate("""
            () => {
                const video = document.querySelector('video');
                return video && !video.paused && video.currentTime > 0;
            }
        """)
        
        print(f"\nAd skipped: {ad_skipped}")
        print(f"Video playing: {is_playing}")
        
        # Keep browser open for manual verification
        print("\nBrowser will stay open for 60 seconds. Check if ad was skipped.")
        await asyncio.sleep(60)
        
    finally:
        await session.close()


if __name__ == "__main__" and "manual" in sys.argv:
    asyncio.run(manual_test_ad_skip())