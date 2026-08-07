"""
Send WhatsApp message to "Mom" via WhatsApp Desktop app using keyboard shortcuts.
Run: python send_whatsapp_app_mom.py
"""

import sys
import time
sys.path.insert(0, r'D:\Ansh Kesharwani\Documents\indus-phase1\indus')

from pywinauto import Desktop, Application


def send_via_keyboard_shortcuts():
    """Send message using keyboard shortcuts in WhatsApp Desktop."""
    try:
        print("Finding WhatsApp Desktop window...")
        windows = Desktop(backend="uia").windows()
        window = None
        for w in windows:
            if "whatsapp" in w.window_text().lower():
                window = w
                break
        
        if not window:
            print("WhatsApp Desktop not found!")
            return False
        
        print("Found: " + window.window_text())
        window.set_focus()
        time.sleep(0.5)
        
        # WhatsApp Desktop keyboard shortcuts:
        # Ctrl+F - Search
        # Type contact name
        # Enter - Select contact
        # Type message
        # Enter - Send
        
        print("Sending Ctrl+F to search...")
        window.type_keys("^f")  # Ctrl+F
        time.sleep(0.5)
        
        print("Typing contact name: Mom")
        window.type_keys("Mom")
        time.sleep(1.5)
        
        print("Pressing Enter to select contact...")
        window.type_keys("{ENTER}")
        time.sleep(1)
        
        print("Typing message: hello from app")
        window.type_keys("hello from app")
        time.sleep(0.5)
        
        print("Pressing Enter to send...")
        window.type_keys("{ENTER}")
        time.sleep(0.5)
        
        print("Message sent!")
        return True
        
    except Exception as e:
        print("Error: " + str(e))
        import traceback
        traceback.print_exc()
        return False


def main():
    print("Sending via WhatsApp Desktop app keyboard shortcuts...")
    success = send_via_keyboard_shortcuts()
    
    if success:
        print("\n[SUCCESS] Message sent via app!")
    else:
        print("\n[FAILED] Could not send via app")


if __name__ == "__main__":
    main()