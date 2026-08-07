"""
Send clipboard content to "Ansh Kesharwani" via WhatsApp Web.
Run: python send_clipboard_to_ansh.py
"""

import asyncio
import sys
sys.path.insert(0, r'D:\Ansh Kesharwani\Documents\indus-phase1\indus')

import pyperclip
from core.automation.playwright_automation import WhatsAppWebAutomation


async def send_clipboard_to_ansh():
    """Send clipboard content to Ansh Kesharwani."""
    
    # Get clipboard content
    clipboard_text = pyperclip.paste()
    if not clipboard_text:
        print("Clipboard is empty!")
        return
    
    print("Clipboard content: " + clipboard_text[:100] + ("..." if len(clipboard_text) > 100 else ""))
    
    wa = WhatsAppWebAutomation(
        browser_type="chromium",
        user_data_dir=r"D:\Ansh Kesharwani\Documents\indus-phase1\indus\whatsapp_session"
    )
    
    try:
        print("Opening WhatsApp Web...")
        await wa.initialize(headless=False)
        
        if not wa._logged_in:
            print("Please scan QR code...")
            await wa.wait_for_login(timeout=120000)
        
        print("Logged in!")
        
        # Send to "Ansh Kesharwani"
        print("Sending to 'Ansh Kesharwani'...")
        result = await wa.send_message("Ansh Kesharwani", clipboard_text)
        
        print("Result: " + str(result))
        
        if result["success"]:
            print("Message sent successfully!")
        else:
            print("Failed: " + str(result.get('error')))
        
        print("\nBrowser staying open for 10 seconds...")
        await asyncio.sleep(10)
        
    except Exception as e:
        print("Error: " + str(e))
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(send_clipboard_to_ansh())