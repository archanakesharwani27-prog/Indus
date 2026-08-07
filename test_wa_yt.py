import sys, asyncio, os
sys.path.insert(0, r'D:\Ansh Kesharwani\Documents\indus-phase1\indus')
from core.automation.playwright_automation import (
    WhatsAppWebAutomation, play_youtube_song, BrowserSession
)

async def test_whatsapp_message():
    """Send WhatsApp message with screenshot via WhatsApp Web."""
    print("=== WHATSAPP WEB: Send message + screenshot ===")
    
    wa = WhatsAppWebAutomation()
    await wa.initialize(headless=False)
    
    print("Waiting for QR code scan (60s)...")
    logged_in = await wa.wait_for_login(timeout=60000)
    
    if not logged_in:
        print("Not logged in. Please scan QR code.")
        return False
    
    print("Logged in! Sending message to 'Ansh Kesharwani'...")
    
    # Take screenshot first
    from core.system.screen import get_screen_analyzer
    analyzer = get_screen_analyzer("tesseract")
    image = analyzer.capture_full_screen()
    screenshot_path = r"D:\Ansh Kesharwani\Documents\indus-phase1\indus\whatsapp_screenshot.png"
    analyzer.save_screenshot(image, screenshot_path)
    print("Screenshot saved:", screenshot_path)
    
    # Send message (WhatsApp Web doesn't easily support file attach via automation)
    # We'll send a text message mentioning the screenshot
    result = await wa.send_message(
        "Ansh Kesharwani", 
        "Test from Indus AI: Screenshot captured and VLC playing Spider-Man 2! Time: " + time.strftime("%H:%M:%S")
    )
    print("Message result:", result)
    
    # Keep browser open for 15s to verify
    print("Keeping browser open for 15s...")
    await asyncio.sleep(15)
    
    await wa.close()
    return result.get("success", False)

async def test_youtube_play():
    """Play YouTube video with ad skip."""
    print("\n=== YOUTUBE: Play video with ad skip ===")
    
    result = await play_youtube_song(
        "rick astley never gonna give you up", 
        headless=False,
        keep_open=True
    )
    print("Result:", result)
    
    if result.get("playing"):
        print("Video is playing!")
        print("Keeping browser open for 20s for verification...")
        await asyncio.sleep(20)
    else:
        print("Video may not be playing:", result.get("error"))
    
    return result.get("success", False)

import time

async def main():
    print("Testing WhatsApp Web message + YouTube playback...")
    
    # Test WhatsApp
    wa_ok = await test_whatsapp_message()
    
    # Test YouTube
    yt_ok = await test_youtube_play()
    
    print("\n=== SUMMARY ===")
    print("WhatsApp message:", "PASS" if wa_ok else "FAIL")
    print("YouTube playback:", "PASS" if yt_ok else "FAIL")

if __name__ == "__main__":
    asyncio.run(main())