"""
Send WhatsApp message to "Mom" via WhatsApp Web with persistent session.
Run: python send_whatsapp_web_mom.py
"""

import asyncio
import sys
sys.path.insert(0, r'D:\Ansh Kesharwani\Documents\indus-phase1\indus')

from core.automation.playwright_automation import WhatsAppWebAutomation


async def send_to_mom():
    """Send hello message to Mom on WhatsApp Web."""
    
    wa = WhatsAppWebAutomation(
        browser_type="chromium",
        user_data_dir=r"D:\Ansh Kesharwani\Documents\indus-phase1\indus\whatsapp_session"
    )
    
    try:
        print("Opening WhatsApp Web (persistent session)...")
        await wa.initialize(headless=False)
        
        if not wa._logged_in:
            print("\n[QR CODE REQUIRED] Please scan the QR code in the browser window.")
            print("Waiting for login (120 seconds)...")
            logged_in = await wa.wait_for_login(timeout=120000)
            
            if not logged_in:
                print("Login timeout.")
                return
            
            print("Logged in successfully!")
        else:
            print("Already logged in (session restored)!")
        
        # Send message to "Mom" (exact name from contact list)
        print("\nSending message to 'Mom'...")
        result = await wa.send_message("Mom", "hello")
        
        print("Result: " + str(result))
        
        if result["success"]:
            print("Message sent successfully!")
        else:
            print("Failed: " + str(result.get('error')))
        
        print("\nBrowser staying open for 15 seconds...")
        await asyncio.sleep(15)
        
    except Exception as e:
        print("Error: " + str(e))
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(send_to_mom())