# ui/avatar_widget.py
"""
INDUS Avatar System -- PyQt6 Presentation Widget
Encapsulates AvatarController and AvatarRenderer in a standalone or embeddable QWidget.
Renders real-time layered avatar animations at 60 FPS with zero blocking of the Qt event loop.
"""

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QTimer, QPointF
from PyQt6.QtGui import QPainter, QPixmap, QMouseEvent
from PyQt6.QtWidgets import QWidget, QSizePolicy

from core.avatar import AvatarController, AvatarRenderer, AvatarState, GazeDirection, EmotionType


class AvatarWidget(QWidget):
    """
    Dedicated PyQt6 Presentation widget for the INDUS Avatar.
    Connects to an AvatarController and paints layered frames on paintEvent.
    """

    def __init__(self, face_path: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.setMouseTracking(True)
        self.setMinimumSize(220, 220)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Load face image
        face_pixmap = None
        if face_path and Path(face_path).exists():
            face_pixmap = QPixmap(face_path)

        self.controller = AvatarController()
        self.renderer = AvatarRenderer(face_pixmap)

        # 60 FPS update timer (16ms)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)
        self._timer.start(16)

    def set_face_image(self, pixmap: QPixmap):
        """Set or update avatar face image."""
        self.renderer.set_face_pixmap(pixmap)

    def mouseMoveEvent(self, event: QMouseEvent):
        """Forward mouse tracking to the GazeController."""
        pos = event.position()
        self.controller.follow_cursor(pos.x(), pos.y(), self.width(), self.height())
        super().mouseMoveEvent(event)

    def _on_tick(self):
        """Step avatar controller physics and request repainting."""
        self.controller.update()
        self.update()

    def paintEvent(self, _):
        """Render the composite avatar onto the widget canvas."""
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        W, H = self.width(), self.height()
        cx, cy = W / 2.0, H / 2.0
        fw = min(W, H) * 0.90

        # Delegate rendering to AvatarRenderer
        self.renderer.render(p, cx, cy, fw, self.controller.state, self.controller.fx)
