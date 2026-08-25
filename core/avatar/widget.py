# core/avatar/widget.py
"""
INDUS Avatar System -- Layered 2-Layer PyQt6 Avatar Widget
Base QLabel (face/gaze/blink) + Transparent Mouth Overlay QLabel with responsive geometry sync.
"""

from typing import Optional
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QResizeEvent
from PyQt6.QtWidgets import QWidget, QLabel

from core.avatar.avatar_state import AvatarState
from core.avatar.emotion_manager import IndusEmotionFaceManager


class AvatarWidget(QWidget):
    def __init__(self, parent=None, face_manager: Optional[IndusEmotionFaceManager] = None):
        super().__init__(parent)
        self.setMinimumSize(220, 220)

        # 1. Base Face Layer
        self.base = QLabel(self)
        self.base.setScaledContents(True)
        self.base.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 2. Transparent Mouth Overlay Layer
        self.mouth = QLabel(self)
        self.mouth.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.mouth.setScaledContents(True)
        self.mouth.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.manager = face_manager or IndusEmotionFaceManager(self)
        self.manager.avatar = self

        self._sync_geometry()
        self.manager._update_face()
        self.manager._update_mouth()

    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)
        self._sync_geometry()

    def _sync_geometry(self):
        self.base.setGeometry(self.rect())

        width = int(self.width() * 0.42)
        height = int(self.height() * 0.22)
        x = (self.width() - width) // 2
        y = int(self.height() * 0.61)

        self.mouth.setGeometry(x, y, width, height)

    def update_face_layer(self, pixmap: Optional[QPixmap]):
        if pixmap and not pixmap.isNull():
            self.base.setPixmap(pixmap)

    def update_mouth_layer(self, pixmap: Optional[QPixmap]):
        if pixmap and not pixmap.isNull():
            self.mouth.setPixmap(pixmap)
            self.mouth.setVisible(True)
        else:
            self.mouth.clear()
            self.mouth.setVisible(False)
