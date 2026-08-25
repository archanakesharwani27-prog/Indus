# core/image_card/card_widget.py
"""
INDUS Neural Image Synthesis HUD Card Widget
==============================================
A futuristic floating overlay card displaying AI-generated images with:
- High-definition image display
- Prompt / Architecture metadata chip
- Quick actions: Set as Wallpaper, Open in Viewer, Copy File Path, Dismiss
"""

from __future__ import annotations
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

from PyQt6.QtCore import (
    QEasingCurve, QPoint, QPropertyAnimation, Qt, QTimer, pyqtSignal,
)
from PyQt6.QtGui import QColor, QFont, QPainter, QBrush, QPen, QPixmap
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

_BG      = '#030810'
_PANEL   = '#060F1C'
_BORDER  = '#0F2A4A'
_BORDER2 = '#1A4A7A'
_CYAN    = '#00FFFF'
_CYAN_D  = '#008A8A'
_CYAN_G  = '#001A1A'
_MAGENTA = '#FF007F'
_WHITE   = '#FFFFFF'
_TEXT    = '#4ADDE8'
_TEXT_MUTED = '#8BAAB8'
_MONO    = 'Consolas'
_UI      = 'Segoe UI'
_CARD_W  = 440
_CARD_H  = 480
_SLIDE_MS = 400
_SLIDEOUT_MS = 280
_AUTODISMISS_S = 45


class ImageCardWidget(QWidget):
    """Floating HUD Image Generation Preview Card."""

    closed = pyqtSignal()

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.setFixedSize(_CARD_W, _CARD_H)
        self._current_image_path = ""
        self._x_final = 0
        self._y_final = 0
        self._slide_in_anim  = None
        self._slide_out_anim = None

        self._dismiss_tmr = QTimer(self)
        self._dismiss_tmr.setSingleShot(True)
        self._dismiss_tmr.timeout.connect(self.hide_card)

        self._build_ui()
        self.hide()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._frame = QFrame(self)
        self._frame.setObjectName("ImageCardFrame")
        self._frame.setStyleSheet(f"""
            QFrame#ImageCardFrame {{
                background: {_BG};
                border: 1.5px solid {_CYAN};
                border-radius: 8px;
            }}
        """)
        outer.addWidget(self._frame)

        root = QVBoxLayout(self._frame)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # 1. HEADER
        hdr = QWidget()
        hdr.setFixedHeight(44)
        hdr.setStyleSheet(f"background: {_PANEL}; border-bottom: 1px solid {_BORDER2}; border-top-left-radius: 7px; border-top-right-radius: 7px;")
        hdr_lay = QHBoxLayout(hdr)
        hdr_lay.setContentsMargins(14, 0, 14, 0)
        hdr_lay.setSpacing(8)

        icon = QLabel("🎨")
        icon.setFont(QFont(_MONO, 12))
        icon.setStyleSheet("background: transparent;")
        hdr_lay.addWidget(icon)

        title = QLabel("NEURAL IMAGE SYNTHESIS")
        title.setFont(QFont(_MONO, 9, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {_CYAN}; letter-spacing: 2px; background: transparent;")
        hdr_lay.addWidget(title)

        hdr_lay.addStretch()

        self._close_btn = QPushButton("✓")
        self._close_btn.setFixedSize(28, 28)
        self._close_btn.setFont(QFont(_MONO, 10, QFont.Weight.Bold))
        self._close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._close_btn.setStyleSheet(f"""
            QPushButton {{
                background: {_PANEL};
                color: {_CYAN};
                border: 1px solid {_BORDER2};
                border-radius: 14px;
            }}
            QPushButton:hover {{
                background: {_CYAN_G};
                color: {_WHITE};
                border-color: {_CYAN};
            }}
        """)
        self._close_btn.clicked.connect(self.hide_card)
        hdr_lay.addWidget(self._close_btn)
        root.addWidget(hdr)

        # 2. BODY
        body = QWidget()
        body.setStyleSheet("background: transparent;")
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(16, 12, 16, 12)
        body_lay.setSpacing(10)

        # Image Container
        self._img_container = QLabel()
        self._img_container.setFixedSize(406, 270)
        self._img_container.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._img_container.setStyleSheet(f"""
            background: {_PANEL};
            border: 1px solid {_BORDER2};
            border-radius: 6px;
        """)
        body_lay.addWidget(self._img_container)

        # Prompt & Meta Labels
        self._prompt_lbl = QLabel("Prompt description here...")
        self._prompt_lbl.setFont(QFont(_UI, 9))
        self._prompt_lbl.setWordWrap(True)
        self._prompt_lbl.setStyleSheet(f"color: {_WHITE}; background: transparent;")
        body_lay.addWidget(self._prompt_lbl)

        meta_row = QHBoxLayout()
        meta_row.setContentsMargins(0, 0, 0, 0)

        self._model_badge = QLabel("FLUX.1-SCHNELL // 1024x1024")
        self._model_badge.setFont(QFont(_MONO, 7, QFont.Weight.Bold))
        self._model_badge.setStyleSheet(f"""
            color: {_CYAN};
            background: {_PANEL};
            border: 1px solid {_BORDER};
            border-radius: 4px;
            padding: 3px 8px;
        """)
        meta_row.addWidget(self._model_badge)
        meta_row.addStretch()
        body_lay.addLayout(meta_row)

        # Action Buttons Row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.setContentsMargins(0, 4, 0, 0)

        self._btn_wallpaper = QPushButton("🖼️ Set Wallpaper")
        self._btn_wallpaper.setFixedHeight(32)
        self._btn_wallpaper.setFont(QFont(_UI, 9, QFont.Weight.Bold))
        self._btn_wallpaper.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_wallpaper.setStyleSheet(f"""
            QPushButton {{
                background: {_PANEL};
                color: {_CYAN};
                border: 1px solid {_BORDER2};
                border-radius: 5px;
                padding: 4px 12px;
            }}
            QPushButton:hover {{
                background: #003344;
                color: {_WHITE};
                border-color: {_CYAN};
            }}
        """)
        self._btn_wallpaper.clicked.connect(self._set_wallpaper_action)
        btn_row.addWidget(self._btn_wallpaper)

        self._btn_open = QPushButton("↗ Open Fullscreen")
        self._btn_open.setFixedHeight(32)
        self._btn_open.setFont(QFont(_UI, 9, QFont.Weight.Bold))
        self._btn_open.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_open.setStyleSheet(f"""
            QPushButton {{
                background: {_PANEL};
                color: {_TEXT};
                border: 1px solid {_BORDER2};
                border-radius: 5px;
                padding: 4px 12px;
            }}
            QPushButton:hover {{
                background: #061A2E;
                color: {_WHITE};
                border-color: {_TEXT};
            }}
        """)
        self._btn_open.clicked.connect(self._open_image_action)
        btn_row.addWidget(self._btn_open)

        body_lay.addLayout(btn_row)
        root.addWidget(body, stretch=1)

    # ---- Public API ----
    def show_generated_image(self, data: Dict[str, Any]):
        """Populate image card data and slide into viewport."""
        img_path = str(data.get("image_path", ""))
        prompt = str(data.get("prompt", "Neural synthesized artwork"))
        model_name = str(data.get("model", "FLUX.1-HD"))
        dims = str(data.get("dimensions", "1024x1024"))

        self._current_image_path = img_path

        # Set Prompt (truncated if long)
        p_display = prompt if len(prompt) < 110 else prompt[:107] + "..."
        self._prompt_lbl.setText(f'"{p_display}"')
        self._model_badge.setText(f"{model_name.upper()} // {dims}")

        # Load and scale image to fit container
        if img_path and os.path.exists(img_path):
            pixmap = QPixmap(img_path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    self._img_container.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self._img_container.setPixmap(scaled)
            else:
                self._img_container.setText("Image preview unavailable")
        else:
            self._img_container.setText("Rendering visual asset...")

        self._position_card()
        self.show()
        self.raise_()
        self._animate_in()
        self._dismiss_tmr.start(_AUTODISMISS_S * 1000)

    def hide_card(self):
        self._dismiss_tmr.stop()
        self._animate_out()

    def _set_wallpaper_action(self):
        if self._current_image_path and os.path.exists(self._current_image_path):
            try:
                import ctypes
                SPI_SETDESKWALLPAPER = 20
                ctypes.windll.user32.SystemParametersInfoW(SPI_SETDESKWALLPAPER, 0, str(Path(self._current_image_path).resolve()), 3)
                self._btn_wallpaper.setText("✓ Wallpaper Set!")
            except Exception as e:
                self._btn_wallpaper.setText("Wallpaper Failed")

    def _open_image_action(self):
        if self._current_image_path and os.path.exists(self._current_image_path):
            try:
                os.startfile(self._current_image_path)
            except Exception:
                try:
                    subprocess.Popen(["explorer.exe", str(self._current_image_path)])
                except Exception:
                    pass

    # ---- Internal Positioning & Animation ----
    def _position_card(self):
        parent = self.parent()
        if parent is None:
            return
        pw, ph = parent.width(), parent.height()
        self._x_final = pw - _CARD_W - 16
        self._y_final = (ph - _CARD_H) // 2
        self.setGeometry(pw + 10, self._y_final, _CARD_W, _CARD_H)

    def _animate_in(self):
        anim = QPropertyAnimation(self, b"pos", self)
        anim.setDuration(_SLIDE_MS)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.setStartValue(QPoint(self.x(), self._y_final))
        anim.setEndValue(QPoint(self._x_final, self._y_final))
        self._slide_in_anim = anim
        anim.start()

    def _animate_out(self):
        parent = self.parent()
        x_off = (parent.width() + 20) if parent else (self._x_final + _CARD_W + 20)
        anim = QPropertyAnimation(self, b"pos", self)
        anim.setDuration(_SLIDEOUT_MS)
        anim.setEasingCurve(QEasingCurve.Type.InCubic)
        anim.setStartValue(QPoint(self._x_final, self._y_final))
        anim.setEndValue(QPoint(x_off, self._y_final))
        anim.finished.connect(self._on_out_done)
        self._slide_out_anim = anim
        anim.start()

    def _on_out_done(self):
        self.hide()
        self.closed.emit()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        for i in range(6, 0, -1):
            shadow_col = QColor(0, 255, 255, int(18 * (1 - i / 7)))
            painter.setBrush(QBrush(shadow_col))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(i, i, _CARD_W - i*2, _CARD_H - i*2, 8, 8)
