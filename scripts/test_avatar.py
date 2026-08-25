# scripts/test_avatar.py
"""
INDUS Avatar System -- Interactive Standalone Developer Demo
Tests all emotional expressions, 9-directional eye gaze, smooth target tracking,
natural blinking, and voice-driven lip-sync with synthetic PCM audio streams.

Keyboard Controls:
  [1] Neutral      [2] Happy        [3] Sad          [4] Thinking     [5] Surprised
  [W] Look Up      [A] Look Left    [S] Look Down    [D] Look Right   [C] Center
  [B] Trigger Blink                 [L] Listening    [T] Thinking
  [SPACE] Simulate Speaking & Lip-Sync (Synthetic Audio Stream)
  [ESC] Exit
"""

import math
import os
import struct
import sys
from pathlib import Path

# Add project root to Python path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor, QPainter, QKeyEvent
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QLabel, QWidget, QFrame

from ui.avatar_widget import AvatarWidget
from core.avatar import EmotionType, GazeDirection, OperationalState


class AvatarDemoWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("INDUS Avatar System -- Interactive Developer Harness")
        self.resize(780, 680)
        self.setStyleSheet("background-color: #000000; color: #00FFFF;")

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(10)

        # Header Title
        hdr = QLabel("INDUS AVATAR INTELLIGENCE & RENDERING ENGINE")
        hdr.setFont(QFont("Consolas", 12, QFont.Weight.Bold))
        hdr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hdr.setStyleSheet("color: #00FFFF; letter-spacing: 2px;")
        layout.addWidget(hdr)

        # Avatar presentation widget
        face_path = str(ROOT_DIR / "face.png")
        self.avatar_widget = AvatarWidget(face_path=face_path)
        layout.addWidget(self.avatar_widget, stretch=1)

        # Status & Control Legend
        self.status_lbl = QLabel("STATUS: IDLE | EMOTION: NEUTRAL | GAZE: CENTER | LIP-SYNC: CLOSED")
        self.status_lbl.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_lbl.setStyleSheet("color: #FFFFFF; background: #030810; padding: 6px; border: 1px solid #0F2A4A;")
        layout.addWidget(self.status_lbl)

        controls = QLabel(
            "HOTKEYS:  [1-5] Emotions (Neutral/Happy/Sad/Think/Surprise) | [WASD] Look Dir | [C] Center
"
            "          [B] Blink | [L] Listening | [T] Thinking | [SPACE] Speak / Synthetic Lip-Sync"
        )
        controls.setFont(QFont("Consolas", 8))
        controls.setAlignment(Qt.AlignmentFlag.AlignCenter)
        controls.setStyleSheet("color: #1C5060;")
        layout.addWidget(controls)

        # Synthetic Audio Generator for SPACE key
        self._is_speaking_synthetic = False
        self._speech_phase = 0.0
        self._speech_timer = QTimer(self)
        self._speech_timer.timeout.connect(self._generate_synthetic_speech_chunk)

        # Status updater
        self._status_timer = QTimer(self)
        self._status_timer.timeout.connect(self._update_status_bar)
        self._status_timer.start(50)

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        ctrl = self.avatar_widget.controller

        # Emotions 1-5
        if key == Qt.Key.Key_1:
            ctrl.set_emotion(EmotionType.NEUTRAL)
        elif key == Qt.Key.Key_2:
            ctrl.set_emotion(EmotionType.HAPPY)
        elif key == Qt.Key.Key_3:
            ctrl.set_emotion(EmotionType.SAD)
        elif key == Qt.Key.Key_4:
            ctrl.set_emotion(EmotionType.THINKING)
        elif key == Qt.Key.Key_5:
            ctrl.set_emotion(EmotionType.SURPRISED)

        # Gaze WASD + C
        elif key == Qt.Key.Key_W:
            ctrl.look_direction(GazeDirection.UP)
        elif key == Qt.Key.Key_A:
            ctrl.look_direction(GazeDirection.LEFT)
        elif key == Qt.Key.Key_S:
            ctrl.look_direction(GazeDirection.DOWN)
        elif key == Qt.Key.Key_D:
            ctrl.look_direction(GazeDirection.RIGHT)
        elif key == Qt.Key.Key_C:
            ctrl.look_center()

        # Blink
        elif key == Qt.Key.Key_B:
            ctrl.start_blink()

        # Operational States
        elif key == Qt.Key.Key_L:
            ctrl.set_listening(True)
        elif key == Qt.Key.Key_T:
            ctrl.set_thinking(True)

        # Simulated Speaking with synthetic PCM audio
        elif key == Qt.Key.Key_Space:
            if not self._is_speaking_synthetic:
                self._is_speaking_synthetic = True
                ctrl.start_speaking()
                self._speech_timer.start(25) # 40 chunks/sec
            else:
                self._is_speaking_synthetic = False
                self._speech_timer.stop()
                ctrl.stop_speaking()

        elif key == Qt.Key.Key_Escape:
            self.close()

        super().keyPressEvent(event)

    def _generate_synthetic_speech_chunk(self):
        """Generates 16kHz PCM audio wave buffer with natural speech syllable cadence."""
        ctrl = self.avatar_widget.controller
        num_samples = 400 # 25ms at 16kHz
        samples = []

        # Modulated speech syllable amplitude (0 to 30000)
        self._speech_phase += 0.15
        cadence = 0.5 + 0.45 * math.sin(self._speech_phase) + 0.3 * math.sin(self._speech_phase * 2.3)
        amplitude = max(0.0, min(1.0, cadence)) * 28000.0

        for i in range(num_samples):
            # Formant carrier frequency ~220Hz
            val = int(amplitude * math.sin(i * 0.086))
            samples.append(max(-32767, min(32767, val)))

        pcm_bytes = struct.pack(f"<{num_samples}h", *samples)
        ctrl.process_audio_chunk(pcm_bytes)

    def _update_status_bar(self):
        st = self.avatar_widget.controller.state
        self.status_lbl.setText(
            f"STATE: {st.operational_state.value.upper()} | "
            f"EMOTION: {st.current_emotion.value.upper()} | "
            f"GAZE: ({st.gaze_x:+.2f}, {st.gaze_y:+.2f}) | "
            f"MOUTH: {st.mouth_shape.value.upper()} ({st.mouth_openness*100:.0f}%) | "
            f"BLINK: {st.blink_state.value.upper()}"
        )


def main():
    app = QApplication(sys.argv)
    win = AvatarDemoWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
