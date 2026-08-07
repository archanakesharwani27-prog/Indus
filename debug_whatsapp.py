"""
Debug WhatsApp Desktop UI structure.
Run: python debug_whatsapp.py
"""

import sys
import time
sys.path.insert(0, r'D:\Ansh Kesharwani\Documents\indus-phase1\indus')

from pywinauto import Desktop


def main():
    print("Searching for WhatsApp Desktop window...")
    windows = Desktop(backend="uia").windows()
    window = None
    for w in windows:
        if "whatsapp" in w.window_text().lower():
            window = w
            break
    
    if not window:
        print("WhatsApp Desktop window not found!")
        return
    
    print("Found: %s" % window.window_text())
    window.set_focus()
    time.sleep(0.5)
    
    print("\n=== ALL CONTROLS ===")
    try:
        for ctrl in window.descendants():
            text = ctrl.window_text()[:80]
            auto_id = ctrl.auto_id()
            ctype = ctrl.control_type()
            if text or auto_id:
                print("  [%s] text='%s' auto_id='%s'" % (ctype, text, auto_id))
    except Exception as e:
        print("Error: %s" % e)
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()