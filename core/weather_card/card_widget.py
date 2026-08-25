# core/weather_card/card_widget.py
"""
INDUS Weather Card Widget
==========================
A futuristic HUD floating overlay card that slides in from the right
when INDUS fetches or reports atmospheric meteorological telemetry.
"""

from __future__ import annotations
from typing import Dict, Any
from PyQt6.QtCore import (
    QEasingCurve, QPoint, QPropertyAnimation, Qt, QTimer, pyqtSignal,
)
from PyQt6.QtGui import QColor, QFont, QPainter, QBrush, QPen
from PyQt6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton,
    QVBoxLayout, QWidget,
)

_BG      = '#030810'
_PANEL   = '#060F1C'
_BORDER  = '#0F2A4A'
_BORDER2 = '#1A4A7A'
_CYAN    = '#00FFFF'
_CYAN_D  = '#008A8A'
_CYAN_G  = '#001A1A'
_AMBER   = '#FFB300'
_WHITE   = '#FFFFFF'
_DIM     = '#1C5060'
_TEXT    = '#4ADDE8'
_TEXT_MUTED = '#8BAAB8'
_MONO    = 'Consolas'
_UI      = 'Segoe UI'
_CARD_W  = 430
_CARD_H  = 380
_SLIDE_MS = 400
_SLIDEOUT_MS = 280
_AUTODISMISS_S = 35

WEATHER_GLYPHS = {
    'clear': '☀️',
    'sunny': '☀️',
    'partly cloudy': '⛅',
    'cloudy': '☁️',
    'overcast': '☁️',
    'mist': '🌫️',
    'fog': '🌫️',
    'rain': '🌧️',
    'patchy rain': '🌦️',
    'light rain': '🌦️',
    'heavy rain': '🌧️',
    'thunderstorm': '⛈️',
    'snow': '❄️',
    'blizzard': '❄️',
}

def _get_glyph(condition: str) -> str:
    c = (condition or '').lower()
    for k, v in WEATHER_GLYPHS.items():
        if k in c:
            return v
    return '⛅'


class _MetricBox(QFrame):
    """Telemetry measurement display box."""
    def __init__(self, label: str, value: str, icon: str = ''):
        super().__init__()
        self.setStyleSheet(f"""
            QFrame {{
                background: {_PANEL};
                border: 1px solid {_BORDER};
                border-radius: 5px;
                padding: 4px;
            }}
            QFrame:hover {{
                border-color: {_BORDER2};
            }}
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(3)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel(f"{icon} {label}".strip())
        lbl.setFont(QFont(_MONO, 7, QFont.Weight.Bold))
        lbl.setStyleSheet(f"color: {_CYAN_D}; letter-spacing: 1px; background: transparent;")
        top_row.addWidget(lbl)
        top_row.addStretch()
        lay.addLayout(top_row)

        self._val_lbl = QLabel(value)
        self._val_lbl.setFont(QFont(_MONO, 11, QFont.Weight.Bold))
        self._val_lbl.setStyleSheet(f"color: {_WHITE}; background: transparent;")
        lay.addWidget(self._val_lbl)

    def set_value(self, val: str):
        self._val_lbl.setText(val)


class WeatherCardWidget(QWidget):
    """Floating animated INDUS Weather Card overlay."""

    closed = pyqtSignal()

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.setFixedSize(_CARD_W, _CARD_H)
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
        self._frame.setObjectName("WeatherCardFrame")
        self._frame.setStyleSheet(f"""
            QFrame#WeatherCardFrame {{
                background: {_BG};
                border: 1.5px solid {_BORDER2};
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

        icon = QLabel("🛰️")
        icon.setFont(QFont(_MONO, 12))
        icon.setStyleSheet("background: transparent;")
        hdr_lay.addWidget(icon)

        title = QLabel("ATMOSPHERIC  RADAR")
        title.setFont(QFont(_MONO, 9, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {_CYAN}; letter-spacing: 2.5px; background: transparent;")
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
        body_lay.setContentsMargins(18, 14, 18, 14)
        body_lay.setSpacing(12)

        # Top City & Condition row
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)

        city_col = QVBoxLayout()
        city_col.setSpacing(2)
        self._city_lbl = QLabel("DELHI, IN")
        self._city_lbl.setFont(QFont(_UI, 14, QFont.Weight.Bold))
        self._city_lbl.setStyleSheet(f"color: {_WHITE}; letter-spacing: 1px; background: transparent;")
        city_col.addWidget(self._city_lbl)

        self._cond_lbl = QLabel("☀️ Clear Skies")
        self._cond_lbl.setFont(QFont(_UI, 10))
        self._cond_lbl.setStyleSheet(f"color: {_TEXT}; background: transparent;")
        city_col.addWidget(self._cond_lbl)
        top_row.addLayout(city_col, stretch=1)

        # High / Low badge
        self._hilow_lbl = QLabel("H: 38°  L: 29°")
        self._hilow_lbl.setFont(QFont(_MONO, 8, QFont.Weight.Bold))
        self._hilow_lbl.setStyleSheet(f"""
            color: {_AMBER};
            background: {_PANEL};
            border: 1px solid {_BORDER};
            border-radius: 4px;
            padding: 4px 8px;
        """)
        top_row.addWidget(self._hilow_lbl, alignment=Qt.AlignmentFlag.AlignTop)
        body_lay.addLayout(top_row)

        # Center Main Temperature Hero Block
        hero_row = QHBoxLayout()
        hero_row.setContentsMargins(0, 4, 0, 4)
        hero_row.setSpacing(14)

        self._glyph_lbl = QLabel("☀️")
        self._glyph_lbl.setFont(QFont(_UI, 36))
        self._glyph_lbl.setStyleSheet("background: transparent;")
        hero_row.addWidget(self._glyph_lbl)

        temp_col = QVBoxLayout()
        temp_col.setSpacing(0)
        self._temp_lbl = QLabel("31°C")
        self._temp_lbl.setFont(QFont(_UI, 34, QFont.Weight.Bold))
        self._temp_lbl.setStyleSheet(f"color: {_WHITE}; letter-spacing: -1px; background: transparent;")
        temp_col.addWidget(self._temp_lbl)

        self._feels_lbl = QLabel("FEELS LIKE 35°C")
        self._feels_lbl.setFont(QFont(_MONO, 8, QFont.Weight.Bold))
        self._feels_lbl.setStyleSheet(f"color: {_CYAN}; letter-spacing: 1.5px; background: transparent;")
        temp_col.addWidget(self._feels_lbl)
        hero_row.addLayout(temp_col)
        hero_row.addStretch()

        body_lay.addLayout(hero_row)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {_BORDER2};")
        body_lay.addWidget(sep)

        # 4-Box Telemetry Grid
        grid = QGridLayout()
        grid.setSpacing(8)
        grid.setContentsMargins(0, 0, 0, 0)

        self._box_humidity = _MetricBox("HUMIDITY", "61%", "💧")
        grid.addWidget(self._box_humidity, 0, 0)

        self._box_wind = _MetricBox("WIND VELOCITY", "8 km/h SE", "💨")
        grid.addWidget(self._box_wind, 0, 1)

        self._box_uv = _MetricBox("UV RADIATION", "0 LOW", "☀️")
        grid.addWidget(self._box_uv, 1, 0)

        self._box_status = _MetricBox("ATMOSPHERE", "STABLE", "🌐")
        grid.addWidget(self._box_status, 1, 1)

        body_lay.addLayout(grid)

        # Bottom Live Status Bar
        footer = QHBoxLayout()
        footer.setContentsMargins(0, 4, 0, 0)
        dot = QLabel("●")
        dot.setFont(QFont(_MONO, 8))
        dot.setStyleSheet(f"color: {_CYAN}; background: transparent;")
        footer.addWidget(dot)

        self._footer_lbl = QLabel("LIVE TELEMETRY STREAM // SYNCHRONIZED")
        self._footer_lbl.setFont(QFont(_MONO, 7, QFont.Weight.Bold))
        self._footer_lbl.setStyleSheet(f"color: {_TEXT_MUTED}; letter-spacing: 1.5px; background: transparent;")
        footer.addWidget(self._footer_lbl)
        footer.addStretch()
        body_lay.addLayout(footer)

        root.addWidget(body, stretch=1)

    # ---- Public API ----
    def show_weather(self, data: Dict[str, Any]):
        """Populate data and slide into viewport."""
        city = str(data.get("city", "Unknown City")).upper()
        cond = str(data.get("condition", "Clear"))
        glyph = _get_glyph(cond)

        self._city_lbl.setText(city)
        self._cond_lbl.setText(f"{glyph}  {cond}")
        self._glyph_lbl.setText(glyph)
        self._temp_lbl.setText(str(data.get("temp", "--°C")))
        self._feels_lbl.setText(f"FEELS LIKE {data.get('feels_like', '--°C')}".upper())
        self._hilow_lbl.setText(str(data.get("high_low", "H: --°  L: --°")))

        self._box_humidity.set_value(str(data.get("humidity", "--%")))
        self._box_wind.set_value(str(data.get("wind", "-- km/h")))
        uv = str(data.get("uv_index", "0"))
        self._box_uv.set_value(f"UV {uv}")
        self._box_status.set_value("OPTIMAL")

        self._position_card()
        self.show()
        self.raise_()
        self._animate_in()
        self._dismiss_tmr.start(_AUTODISMISS_S * 1000)

    def hide_card(self):
        self._dismiss_tmr.stop()
        self._animate_out()

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
            shadow_col = QColor(0, 255, 255, int(15 * (1 - i / 7)))
            painter.setBrush(QBrush(shadow_col))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(i, i, _CARD_W - i*2, _CARD_H - i*2, 8, 8)
