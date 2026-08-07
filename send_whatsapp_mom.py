"""
Send WhatsApp message to "mom" via WhatsApp Web.
Run: python send_whatsapp_mom.py
"""

import asyncio
import sys
sys.path.insert(0, r'D:\Ansh Kesharwani\Documents\indus-phase1\indus')

from core.automation.playwright_automation import WhatsAppWebAutomation, send_whatsapp_message


async def send_to_mom():
    """Send hello message to mom on WhatsApp Web."""
    
    # Use the automation class directly for more control
    wa = WhatsAppWebAutomation(browser_type="chromium")
    
    try:
        print("Initializing WhatsApp Web...")
        await wa.initialize(headless=False)
        
        if not wa._logged_in:
            print("\n[QR CODE REQUIRED] Please scan the QR code in the browser window.")
            print("Waiting for login (60 seconds)...")
            logged_in = await wa.wait_for_login(timeout=60000)
            
            if not logged_in:
                print("Login timeout. Please run again and scan QR code faster.")
                return
            
            print("Logged in successfully!")
        else:
            print("Already logged in!")
        
        # Send message to "mom"
        print("\nSending message to 'mom'...")
        result = await wa.send_message("mom", "hello")
        
        print(f"Result: {result}")
        
        if result["success"]:
            print("Message sent successfully!")
        else:
            print(f"Failed: {result.get('error')}")
        
        # Keep browser open for verification
        print("\nBrowser staying open for 15 seconds...")
        await asyncio.sleep(15)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await wa.close()


if __name__ == "__main__":
    asyncio.run(send_to_mom())