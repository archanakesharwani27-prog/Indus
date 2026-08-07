"""
Send WhatsApp message to "Mom" via WhatsApp Web on Microsoft Edge (persistent session).
Run: python send_whatsapp_edge_mom.py
"""

import asyncio
import sys
sys.path.insert(0, r'D:\Ansh Kesharwani\Documents\indus-phase1\indus')

from core.automation.playwright_automation import WhatsAppWebAutomation, BrowserSession


async def send_to_mom_edge():
    """Send hello message to Mom on WhatsApp Web via Edge."""
    
    session = BrowserSession()
    
    try:
        print("Opening WhatsApp Web on Microsoft Edge...")
        from playwright.async_api import async_playwright
        playwright = await async_playwright().start()
        
        # Launch Edge with persistent user data
        context = await playwright.chromium.launch_persistent_context(
            user_data_dir=r"D:\Ansh Kesharwani\Documents\indus-phase1\indus\whatsapp_session_edge",
            headless=False,
            channel="msedge",
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
            args=[
                "--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage",
                "--disable-accelerated-2d-canvas", "--no-first-run", "--no-zygote",
                "--disable-gpu", "--disable-blink-features=AutomationControlled",
            ]
        )
        
        session.browser = None
        session.context = context
        session.page = context.pages[0] if context.pages else await context.new_page()
        session._playwright = playwright
        session._initialized = True
        
        # Go to WhatsApp Web
        await session.navigate_and_wait("https://web.whatsapp.com/")
        
        # Check if logged in
        chat_list_selectors = [
            '[data-testid="chat-list"]', '[data-testid="chatlist"]',
            'div[aria-label="Chat list"]', '#pane-side',
        ]
        
        logged_in = False
        for selector in chat_list_selectors:
            try:
                await session.wait_for_selector(selector, timeout=3000)
                logged_in = True
                print("Already logged in on Edge!")
                break
            except:
                continue
        
        if not logged_in:
            print("\n[QR CODE REQUIRED] Scan QR code in Edge window.")
            print("Waiting 120 seconds...")
            # Wait for login
            start_time = asyncio.get_event_loop().time()
            while (asyncio.get_event_loop().time() - start_time) < 120:
                for selector in chat_list_selectors:
                    try:
                        await session.wait_for_selector(selector, timeout=2000)
                        logged_in = True
                        print("Logged in on Edge!")
                        break
                    except:
                        continue
                if logged_in:
                    break
                await asyncio.sleep(2)
        
        if not logged_in:
            print("Login timeout.")
            return
        
        # Search for Mom
        search_selectors = [
            '[data-testid="chat-list-search"]', '[data-testid="chatlist-search"]',
            'div[aria-label="Search input"]', 'input[placeholder*="Search"]',
        ]
        
        for selector in search_selectors:
            try:
                await session.click_selector(selector, timeout=3000)
                await session.fill_input(selector, "Mom")
                break
            except:
                continue
        
        await asyncio.sleep(2)
        
        # Click contact
        try:
            await session.click_selector('span[title="Mom"]', timeout=5000)
        except:
            await session.click_selector('div[aria-label="Mom"]', timeout=5000)
        
        await asyncio.sleep(1)
        
        # Type message
        msg_selectors = [
            '[data-testid="conversation-compose-box-input"]',
            '[data-testid="compose-box-input"]',
            'div[aria-label="Type a message"]',
            'footer div[contenteditable="true"]',
        ]
        
        for selector in msg_selectors:
            try:
                await session.fill_input(selector, "hello from Edge")
                break
            except:
                continue
        
        await asyncio.sleep(0.5)
        
        # Send
        send_selectors = [
            '[data-testid="compose-btn-send"]', '[data-testid="send-button"]',
            'button[aria-label="Send"]', 'span[data-icon="send"]',
        ]
        
        for selector in send_selectors:
            try:
                await session.click_selector(selector, timeout=3000)
                break
            except:
                continue
        
        print("\n[SUCCESS] Message sent via Microsoft Edge!")
        
        print("\nBrowser open for 15 seconds...")
        await asyncio.sleep(15)
        
    except Exception as e:
        print("Error: " + str(e))
        import traceback
        traceback.print_exc()
    finally:
        try:
            await session.close()
        except:
            pass


if __name__ == "__main__":
    asyncio.run(send_to_mom_edge())