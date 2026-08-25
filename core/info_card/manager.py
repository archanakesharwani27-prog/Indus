# core/info_card/manager.py
from __future__ import annotations
from typing import Optional
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QWidget
from core.info_card.card_widget import InfoCardWidget


class InfoCardManager(QObject):
    """Thread-safe manager for InfoCardWidget lifecycle using Qt signal routing."""

    show_sig = pyqtSignal(str, str)
    update_sig = pyqtSignal(str)
    hide_sig = pyqtSignal()

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self._parent = parent
        self._card: Optional[InfoCardWidget] = None
        self.show_sig.connect(self._gui_show)
        self.update_sig.connect(self._gui_update)
        self.hide_sig.connect(self._gui_hide)

    # -- Thread-safe public API -----------------------------------------
    def show_card(self, query: str, result: str = '') -> None:
        """Show info card. Safe to call from any thread."""
        self.show_sig.emit(str(query or ''), str(result or ''))

    def update_result(self, result: str) -> None:
        """Update card with completed result. Safe to call from any thread."""
        self.update_sig.emit(str(result or ''))

    def hide_card(self) -> None:
        """Slide card out. Safe to call from any thread."""
        self.hide_sig.emit()

    # -- GUI-thread handlers --------------------------------------------
    def _gui_show(self, query: str, result: str) -> None:
        if self._card is None:
            self._card = InfoCardWidget(self._parent)
        self._card.show_card(query, result)
        self._card.raise_()

    def _gui_update(self, result: str) -> None:
        if self._card is not None:
            self._card.update_result(result)
            self._card.raise_()

    def _gui_hide(self) -> None:
        if self._card is not None:
            self._card.hide_card()