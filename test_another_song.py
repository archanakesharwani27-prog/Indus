import asyncio
import sys
sys.path.insert(0, r'D:\Ansh Kesharwani\Documents\indus-phase1\indus')
from core.automation.playwright_automation import BrowserSession

async def test():
    song = 'jubin nautiyal raataan lambiyan'
    session = BrowserSession()
    try:
        await session.initialize(headless=False, browser_type='chromium')
        search_url = f'https://www.youtube.com/results?search_query={song.replace(" ", "+")}'
        await session.navigate_and_wait(search_url)
        await session.wait_for_selector('ytd-video-renderer', timeout=15000)
        await session.click_selector('ytd-video-renderer:first-child #video-title')
        await session.wait_for_selector('.html5-video-player', timeout=15000)
        await session.page.wait_for_function('() => document.querySelector("video").readyState >= 2', timeout=15000)
        await session.evaluate('document.querySelector("video")?.play()')
        await asyncio.sleep(3)
        print('Waiting for ad...')
        result = await session.wait_for_ad_skip(timeout=60000)
        print(f'Ad skipped: {result}')
        is_playing = await session.evaluate('() => { const v = document.querySelector("video"); return v && !v.paused && v.currentTime > 0; }')
        print(f'Playing: {is_playing}')
        await asyncio.sleep(30)
    finally:
        await session.close()

asyncio.run(test())