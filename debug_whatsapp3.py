"""
Debug WhatsApp Desktop UI structure.
Run: python debug_whatsapp3.py
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
    
    print("\n=== FIRST LEVEL CHILDREN ===")
    try:
        children = window.children()
        for i, ctrl in enumerate(children):
            text = ctrl.window_text()[:80]
            print("  [%d] text='%s' | class='%s' | element_info='%s'" % (i, text, ctrl.class_name(), ctrl.element_info))
    except Exception as e:
        print("Error: %s" % e)
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()