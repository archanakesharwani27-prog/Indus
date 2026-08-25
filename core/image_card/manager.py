# core/image_card/manager.py
from __future__ import annotations
from typing import Optional, Dict, Any
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QWidget
from core.image_card.card_widget import ImageCardWidget


class ImageCardManager(QObject):
    """Thread-safe manager for ImageCardWidget lifecycle using Qt signals."""

    show_sig = pyqtSignal(dict)
    hide_sig = pyqtSignal()

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self._parent = parent
        self._card: Optional[ImageCardWidget] = None
        self.show_sig.connect(self._gui_show)
        self.hide_sig.connect(self._gui_hide)

    def show_card(self, data: Dict[str, Any]) -> None:
        """Show image card. Safe to call from any thread."""
        self.show_sig.emit(dict(data or {}))

    def hide_card(self) -> None:
        """Slide image card out. Safe to call from any thread."""
        self.hide_sig.emit()

    def _gui_show(self, data: Dict[str, Any]) -> None:
        if self._card is None:
            self._card = ImageCardWidget(self._parent)
        self._card.show_generated_image(data)
        self._card.raise_()

    def _gui_hide(self) -> None:
        if self._card is not None:
            self._card.hide_card()
