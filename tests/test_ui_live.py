"""
INDUS UI Text Command Test
--------------------------
Starts the JarvisUI, executes text commands, animates visemes and emotions,
and captures visual verification screenshots.
"""

import sys
import os
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QCoreApplication

from ui import JarvisUI
from core.avatar.models import EmotionType, OperationalState, VisemeShape

def main():
    print("[TEST] Starting INDUS UI Live Verification...")
    face_path = os.path.join(PROJECT_ROOT, "face.png")
    ui = JarvisUI(face_path=face_path)
    app = ui._app

    # Warm up UI
    for _ in range(30):
        app.processEvents()
        time.sleep(0.016)

    test_steps = [
        ("1_idle_initial", lambda: ui.set_state("idle")),
        ("2_speaking_start", lambda: ui.set_state("speaking")),
        ("3_feed_hello", lambda: ui.avatar.feed_speech_text("Hello Ansh! Main INDUS hoon.")),
        ("4_happy_emotion", lambda: ui.avatar.detect_and_set_emotion("Bahut accha hai! 😊 Ho gaya!")),
        ("5_feed_bilabials", lambda: ui.avatar.feed_speech_text("Mama papa baby bilabial test.")),
        ("6_thinking_emotion", lambda: ui.avatar.detect_and_set_emotion("Hmm soch raha hoon... 🤔 dekh lete hain.")),
        ("7_excited_emotion", lambda: ui.avatar.detect_and_set_emotion("Zabardast! 🎉 Kaam ho gaya!")),
        ("8_surprised_emotion", lambda: ui.avatar.detect_and_set_emotion("Kya? Sach mein? 😮")),
        ("9_calm_emotion", lambda: ui.avatar.detect_and_set_emotion("Theek hai, shukriya 🙏")),
        ("10_sad_emotion", lambda: ui.avatar.detect_and_set_emotion("Oh nahi... 😢 Fail ho gaya.")),
        ("11_reset_idle", lambda: (ui.avatar.reset_viseme(), ui.set_state("idle"))),
    ]

    screenshot_dir = os.path.join(PROJECT_ROOT, "tests", "screenshots")
    os.makedirs(screenshot_dir, exist_ok=True)

    results = []

    for name, action in test_steps:
        try:
            print(f"[TEST] Executing: {name}")
            action()
            # Run animation loop for 20 frames (~320ms)
            for _ in range(20):
                app.processEvents()
                time.sleep(0.016)

            # Grab screenshot
            pixmap = ui.main_win.grab()
            out_file = os.path.join(screenshot_dir, f"{name}.png")
            pixmap.save(out_file)
            state = ui.avatar.state
            print(f"       -> State: emotion={state.current_emotion.value}, viseme={state.viseme_shape.value}, openness={state.mouth_openness:.2f}")
            results.append((name, "PASS", out_file))
        except Exception as e:
            print(f"[ERROR] {name}: {e}")
            results.append((name, f"FAIL: {e}", None))

    print("\n" + "="*50)
    print("INDUS UI TEST RESULTS")
    print("="*50)
    passed = sum(1 for _, st, _ in results if st == "PASS")
    for name, st, path in results:
        print(f"  [{st}] {name} (screenshot: {path})")
    print(f"\n{passed}/{len(results)} steps passed successfully!")

    # Close window cleanly
    ui.main_win.close()
    app.quit()

if __name__ == "__main__":
    main()
