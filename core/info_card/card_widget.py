# core/info_card/card_widget.py
"""
INDUS Info Card Widget
======================
A frameless floating overlay card that slides in from the right
when INDUS completes a web search / data extraction task.
"""

from __future__ import annotations
import textwrap
from PyQt6.QtCore import (
    QEasingCurve, QPoint, QPropertyAnimation, Qt, QTimer, pyqtSignal,
)
from PyQt6.QtGui import QColor, QFont, QPainter, QBrush
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QProgressBar, QPushButton,
    QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
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
_MONO    = 'Consolas'
_UI      = 'Segoe UI'
_CARD_W  = 430
_CARD_H  = 390
_SLIDE_MS = 400
_SLIDEOUT_MS = 280
_PROGRESS_MS = 1500
_AUTODISMISS_S = 35


def _hud_label(text, size=8, colour=_DIM, bold=False):
    lbl = QLabel(text)
    lbl.setFont(QFont(_MONO, size, QFont.Weight.Bold if bold else QFont.Weight.Normal))
    lbl.setStyleSheet(f'color: {colour}; background: transparent; letter-spacing: 1.5px;')
    return lbl


class InfoCardWidget(QWidget):
    """Floating animated INDUS Info Card overlay."""

    closed = pyqtSignal()

    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.setFixedSize(_CARD_W, _CARD_H)
        self._x_final = 0
        self._y_final = 0
        self._progress_val = 0
        self._progress_step = 2
        self._slide_in_anim  = None
        self._slide_out_anim = None
        self._progress_tmr   = None
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
        self._frame.setObjectName('InfoCardFrame')
        self._frame.setStyleSheet(f"""
            QFrame#InfoCardFrame {{
                background: {_BG};
                border: 1.5px solid {_BORDER2};
                border-radius: 6px;
            }}
        """)
        outer.addWidget(self._frame)

        root = QVBoxLayout(self._frame)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # HEADER
        hdr = QWidget()
        hdr.setFixedHeight(44)
        hdr.setStyleSheet(f'background: {_PANEL}; border-bottom: 1px solid {_BORDER2};')
        hdr_lay = QHBoxLayout(hdr)
        hdr_lay.setContentsMargins(14, 0, 14, 0)
        hdr_lay.setSpacing(8)
        icon = QLabel('≋')
        icon.setFont(QFont(_MONO, 13, QFont.Weight.Bold))
        icon.setStyleSheet(f'color: {_CYAN}; background: transparent;')
        hdr_lay.addWidget(icon)
        title = QLabel('INDUS  INFO  AGENT')
        title.setFont(QFont(_MONO, 9, QFont.Weight.Bold))
        title.setStyleSheet(f'color: {_CYAN}; background: transparent; letter-spacing: 2.5px;')
        hdr_lay.addWidget(title)
        hdr_lay.addStretch()
        self._close_btn = QPushButton('✓')
        self._close_btn.setFixedSize(28, 28)
        self._close_btn.setFont(QFont(_MONO, 10, QFont.Weight.Bold))
        self._close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._close_btn.setStyleSheet(f"""
            QPushButton {{ background: {_PANEL}; color: {_CYAN};
                border: 1px solid {_BORDER2}; border-radius: 14px; }}
            QPushButton:hover {{ background: {_CYAN_G}; color: {_WHITE};
                border-color: {_CYAN}; }}
        """)
        self._close_btn.clicked.connect(self.hide_card)
        hdr_lay.addWidget(self._close_btn)
        root.addWidget(hdr)

        # BODY
        body = QWidget()
        body.setStyleSheet('background: transparent;')
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(18, 14, 18, 14)
        body_lay.setSpacing(10)

        body_lay.addWidget(_hud_label('ACTIVE QUERY', 7, _CYAN_D))

        query_row = QHBoxLayout()
        query_row.setContentsMargins(0, 0, 0, 0)
        query_row.setSpacing(10)
        bar = QFrame()
        bar.setFixedWidth(3)
        bar.setStyleSheet(f'background: {_CYAN}; border-radius: 1px;')
        query_row.addWidget(bar)
        self._query_lbl = QLabel('--')
        self._query_lbl.setFont(QFont(_UI, 11, QFont.Weight.Bold))
        self._query_lbl.setStyleSheet(f'color: {_WHITE}; background: transparent;')
        self._query_lbl.setWordWrap(True)
        query_row.addWidget(self._query_lbl, stretch=1)
        body_lay.addLayout(query_row)
        body_lay.addSpacing(4)

        self._status_lbl = _hud_label('Searching web...', 8, _TEXT)
        body_lay.addWidget(self._status_lbl)

        self._pbar = QProgressBar()
        self._pbar.setRange(0, 100)
        self._pbar.setValue(0)
        self._pbar.setTextVisible(False)
        self._pbar.setFixedHeight(6)
        self._pbar.setStyleSheet(f"""
            QProgressBar {{ background: {_PANEL}; border: 1px solid {_BORDER};
                border-radius: 3px; }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #008A8A, stop:0.6 {_CYAN}, stop:1 #00FFEE);
                border-radius: 3px; }}
        """)
        body_lay.addWidget(self._pbar)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet(f'background: {_BORDER2};')
        body_lay.addWidget(sep)

        body_lay.addWidget(_hud_label('DATA  EXTRACTED', 7, _CYAN_D))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setStyleSheet(f"""
            QScrollArea {{ background: {_BG}; border: 1px solid {_BORDER};
                border-radius: 4px; }}
            QScrollBar:vertical {{ background: {_PANEL}; width: 5px;
                border-radius: 2px; }}
            QScrollBar::handle:vertical {{ background: {_CYAN_D};
                border-radius: 2px; min-height: 20px; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px; }}
        """)
        self._result_lbl = QLabel()
        self._result_lbl.setFont(QFont(_MONO, 8))
        self._result_lbl.setStyleSheet(f'color: {_TEXT}; background: {_BG}; padding: 8px;')
        self._result_lbl.setWordWrap(True)
        self._result_lbl.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self._result_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        scroll.setWidget(self._result_lbl)
        body_lay.addWidget(scroll, stretch=1)

        root.addWidget(body, stretch=1)

    # ---- Public API ----
    def show_card(self, query, result=''):
        q = textwrap.shorten(query.strip(), width=90, placeholder='...')
        self._query_lbl.setText(q)
        if result:
            self._set_complete(result)
        else:
            self._set_searching()
        self._position_card()
        self.show()
        self.raise_()
        self._animate_in()
        self._dismiss_tmr.start(_AUTODISMISS_S * 1000)

    def update_result(self, result):
        self._set_complete(result)

    def hide_card(self):
        self._dismiss_tmr.stop()
        if self._progress_tmr:
            self._progress_tmr.stop()
        self._animate_out()

    # ---- Internal ----
    def _set_searching(self):
        self._status_lbl.setText(f'Searching web...')
        self._status_lbl.setStyleSheet(
            f'color: {_AMBER}; background: transparent; letter-spacing: 1px;')
        self._pbar.setValue(0)
        self._result_lbl.setText('Fetching data from the web...')
        self._progress_val  = 0
        self._progress_step = max(1, 85 * 50 // _PROGRESS_MS)
        if self._progress_tmr:
            self._progress_tmr.stop()
        self._progress_tmr = QTimer(self)
        self._progress_tmr.setInterval(50)
        self._progress_tmr.timeout.connect(self._tick_progress)
        self._progress_tmr.start()

    def _set_complete(self, result):
        if self._progress_tmr:
            self._progress_tmr.stop()
        self._pbar.setValue(100)
        self._status_lbl.setText('RAG Pipeline Complete & Synthesized.')
        self._status_lbl.setStyleSheet(
            f'color: {_CYAN}; background: transparent; letter-spacing: 1px;')
        clean = result.strip()
        for tok in ['**', '__', '###', '##', '#']:
            clean = clean.replace(tok, '')
        self._result_lbl.setText(clean[:1400] + ('...' if len(clean) > 1400 else ''))

    def _tick_progress(self):
        self._progress_val = min(self._progress_val + self._progress_step, 85)
        self._pbar.setValue(self._progress_val)
        if self._progress_val >= 85:
            self._progress_tmr.stop()

    def _position_card(self):
        parent = self.parent()
        if parent is None:
            return
        pw, ph = parent.width(), parent.height()
        self._x_final = pw - _CARD_W - 16
        self._y_final = (ph - _CARD_H) // 2
        self.setGeometry(pw + 10, self._y_final, _CARD_W, _CARD_H)

    def _animate_in(self):
        anim = QPropertyAnimation(self, b'pos', self)
        anim.setDuration(_SLIDE_MS)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.setStartValue(QPoint(self.x(), self._y_final))
        anim.setEndValue(QPoint(self._x_final, self._y_final))
        self._slide_in_anim = anim
        anim.start()

    def _animate_out(self):
        parent = self.parent()
        x_off = (parent.width() + 20) if parent else (self._x_final + _CARD_W + 20)
        anim = QPropertyAnimation(self, b'pos', self)
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
            painter.drawRoundedRect(i, i, _CARD_W - i*2, _CARD_H - i*2, 7, 7)
