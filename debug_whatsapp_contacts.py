"""
Debug WhatsApp contacts - list available contacts.
Run: python debug_whatsapp_contacts.py
"""

import asyncio
import sys
sys.path.insert(0, r'D:\Ansh Kesharwani\Documents\indus-phase1\indus')

from core.automation.playwright_automation import WhatsAppWebAutomation


def safe_print(text):
    """Print with safe encoding."""
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode('ascii', 'replace').decode('ascii'))


async def list_contacts():
    """List contacts in WhatsApp Web."""
    
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
        
        # Click search
        search_selectors = [
            '[data-testid="chat-list-search"]',
            '[data-testid="chatlist-search"]',
            'div[aria-label="Search input"]',
            'input[placeholder*="Search"]',
        ]
        
        for selector in search_selectors:
            try:
                await wa.session.click_selector(selector, timeout=3000)
                print("Clicked search with: " + selector)
                break
            except:
                continue
        
        await asyncio.sleep(1)
        
        # Get all contact names from chat list
        contacts = await wa.session.evaluate("""
            () => {
                const contacts = [];
                const selectors = [
                    '#pane-side [role="listitem"]',
                    '[data-testid="chat-list"] [role="row"]',
                    'div[aria-label="Chat list"] [role="listitem"]',
                    '#pane-side div[tabindex="-1"]',
                ];
                
                for (const sel of selectors) {
                    const items = document.querySelectorAll(sel);
                    if (items.length > 0) {
                        for (const item of items) {
                            const title = item.querySelector('span[title], [title], [aria-label]');
                            if (title) {
                                const name = title.getAttribute('title') || title.getAttribute('aria-label') || title.textContent;
                                if (name && name.trim()) {
                                    contacts.push(name.trim());
                                }
                            }
                        }
                        break;
                    }
                }
                return [...new Set(contacts)];
            }
        """)
        
        print("\nFound " + str(len(contacts)) + " contacts:")
        for i, c in enumerate(contacts[:50]):
            safe_print("  " + str(i+1) + ". " + c)
        
        if len(contacts) > 50:
            print("  ... and " + str(len(contacts) - 50) + " more")
        
        # Look for mom-like contacts
        mom_keywords = ['mom', 'mum', 'maa', 'mother', 'mummy', 'mommy']
        mom_contacts = [c for c in contacts if any(kw in c.lower() for kw in mom_keywords)]
        if mom_contacts:
            print("\nPossible mom contacts:")
            for c in mom_contacts:
                safe_print("  - " + c)
        else:
            print("\nNo obvious mom contacts found.")
            print("Search for your mom's exact name in the list above.")
        
        print("\nBrowser staying open for 30 seconds...")
        await asyncio.sleep(30)
        
    except Exception as e:
        print("Error: " + str(e))
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(list_contacts())