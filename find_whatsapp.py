import sys
sys.path.insert(0, r'D:\Ansh Kesharwani\Documents\indus-phase1\indus')
from pywinauto import Desktop
windows = Desktop(backend='uia').windows()
for w in windows:
    title = w.window_text()
    if 'whatsapp' in title.lower() or 'whats' in title.lower():
        print('Found: title="%s", class="%s", process=%s' % (title, w.class_name(), w.process_id()))