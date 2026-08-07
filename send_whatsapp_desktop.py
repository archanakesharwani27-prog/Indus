"""
Send WhatsApp message to "mom" via native WhatsApp Desktop app using pywinauto.
Run: python send_whatsapp_desktop.py
"""

import sys
import time
sys.path.insert(0, r'D:\Ansh Kesharwani\Documents\indus-phase1\indus')

try:
    import pywinauto
    from pywinauto import Application, Desktop
    from pywinauto.findwindows import ElementNotFoundError
except ImportError:
    print("pywinauto not installed. Run: pip install pywinauto")
    sys.exit(1)


def find_whatsapp_window():
    """Find the WhatsApp desktop window."""
    try:
        # Search all windows for WhatsApp
        windows = Desktop(backend="uia").windows()
        for w in windows:
            if "whatsapp" in w.window_text().lower():
                print('Found WhatsApp window: title="%s", class="%s", pid=%s' % (w.window_text(), w.class_name(), w.process_id()))
                return w
    except Exception as e:
        print("Error finding window: %s" % e)
    return None


def send_message_to_contact(window, contact_name, message):
    """Send a message to a contact in WhatsApp Desktop."""
    try:
        print("Looking for contact: %s" % contact_name)
        
        # Focus the window
        window.set_focus()
        time.sleep(0.5)
        
        # Try to find search box
        search_box = None
        
        # Try different search box identifiers
        search_patterns = [
            {"auto_id": "SearchTextBox", "control_type": "Edit"},
            {"title": "Search", "control_type": "Edit"},
            {"title_re": ".*[Ss]earch.*", "control_type": "Edit"},
            {"class_name": "TextBox", "control_type": "Edit"},
        ]
        
        for pattern in search_patterns:
            try:
                search_box = window.child_window(**pattern)
                if search_box.exists(timeout=2):
                    print("Found search box with pattern: %s" % pattern)
                    break
            except Exception:
                continue
        
        if not search_box or not search_box.exists():
            # Try to find any edit control
            try:
                edits = window.descendants(control_type="Edit")
                for edit in edits:
                    if edit.exists():
                        search_box = edit
                        print("Found edit control: %s" % edit)
                        break
            except Exception:
                pass
        
        if not search_box:
            print("Could not find search box")
            # Print all controls for debugging
            print("\nAll controls in window:")
            try:
                for ctrl in window.descendants():
                    print("  %s | %s | %s" % (ctrl.control_type(), ctrl.window_text()[:50], ctrl.auto_id()))
            except:
                pass
            return False
        
        # Click search box and type contact name
        search_box.click_input()
        time.sleep(0.3)
        search_box.type_keys("^a")  # Select all
        time.sleep(0.2)
        search_box.type_keys(contact_name)
        time.sleep(1.5)  # Wait for search results
        
        # Find and click the contact in search results
        try:
            contact_item = window.child_window(title=contact_name, control_type="ListItem")
            if contact_item.exists(timeout=3):
                contact_item.click_input()
                print("Clicked contact: %s" % contact_name)
            else:
                # Try partial match
                items = window.descendants(control_type="ListItem")
                for item in items:
                    if contact_name.lower() in item.window_text().lower():
                        item.click_input()
                        print("Clicked contact (partial): %s" % item.window_text())
                        break
        except Exception as e:
            print("Could not find/click contact: %s" % e)
            return False
        
        time.sleep(1)
        
        # Find message input box
        msg_box = None
        msg_patterns = [
            {"auto_id": "MessageTextBox", "control_type": "Edit"},
            {"title": "Type a message", "control_type": "Edit"},
            {"title_re": ".*[Tt]ype.*[Mm]essage.*", "control_type": "Edit"},
            {"class_name": "TextBox", "control_type": "Edit"},
        ]
        
        for pattern in msg_patterns:
            try:
                msg_box = window.child_window(**pattern)
                if msg_box.exists(timeout=2):
                    print("Found message box with pattern: %s" % pattern)
                    break
            except Exception:
                continue
        
        if not msg_box:
            # Try to find the last edit control (usually message input)
            try:
                edits = window.descendants(control_type="Edit")
                if edits:
                    msg_box = edits[-1]
                    print("Using last edit control as message box")
            except Exception:
                pass
        
        if not msg_box:
            print("Could not find message input box")
            return False
        
        # Type message
        msg_box.click_input()
        time.sleep(0.3)
        msg_box.type_keys(message)
        time.sleep(0.5)
        
        # Press Enter to send
        msg_box.type_keys("{ENTER}")
        time.sleep(0.5)
        
        print("Message sent to %s: %s" % (contact_name, message))
        return True
        
    except Exception as e:
        print("Error sending message: %s" % e)
        import traceback
        traceback.print_exc()
        return False


def main():
    print("Searching for WhatsApp Desktop window...")
    window = find_whatsapp_window()
    
    if not window:
        print("WhatsApp Desktop window not found!")
        print("Make sure WhatsApp Desktop is running.")
        return
    
    print("Found WhatsApp window: %s" % window.window_text())
    
    # Send message to "mom"
    success = send_message_to_contact(window, "mom", "hello")
    
    if success:
        print("\nMessage sent successfully!")
    else:
        print("\nFailed to send message")


if __name__ == "__main__":
    main()