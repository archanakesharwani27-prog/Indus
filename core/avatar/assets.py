# core/avatar/assets.py
"""
INDUS Avatar System -- Asset Resolver
Resolves multi-folder facial and mouth sprite assets with graceful procedural fallback.
"""

import sys
from pathlib import Path
from typing import Optional, Dict
from PyQt6.QtGui import QPixmap
from core.avatar.avatar_state import Emotion, MouthState


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent.parent


BASE_DIR = _base_dir()
ASSETS_AVATAR = BASE_DIR / "assets" / "avatar"


class AssetResolver:
    """
    Finds and caches avatar artwork across emotion folders and mouth states.
    """

    def __init__(self, root_dir: Optional[Path] = None):
        self.root_dir = root_dir or ASSETS_AVATAR
        self._pixmap_cache: Dict[str, QPixmap] = {}
        self._fallback_pixmap: Optional[QPixmap] = None

        # Load root face.png as universal fallback
        root_face = BASE_DIR / "face.png"
        if root_face.exists():
            self._fallback_pixmap = QPixmap(str(root_face))

    def get_face_pixmap(self, emotion: Emotion, blinking: bool = False, gaze: str = "center") -> Optional[QPixmap]:
        em_val = emotion.value.lower()
        if blinking:
            rel_path = f"{em_val}/blink_{em_val}.png"
        elif gaze != "center":
            rel_path = f"{em_val}/gaze_{gaze}.png"
        else:
            rel_path = f"{em_val}/face_{em_val}.png"

        target_file = self.root_dir / rel_path
        cache_key = f"face:{rel_path}"

        if cache_key in self._pixmap_cache:
            return self._pixmap_cache[cache_key]

        if target_file.exists():
            px = QPixmap(str(target_file))
            if not px.isNull():
                self._pixmap_cache[cache_key] = px
                return px

        return self._fallback_pixmap

    def get_mouth_pixmap(self, mouth: MouthState) -> Optional[QPixmap]:
        rel_path = f"mouth/mouth_{mouth.value}.png"
        target_file = self.root_dir / rel_path
        cache_key = f"mouth:{mouth.value}"

        if cache_key in self._pixmap_cache:
            return self._pixmap_cache[cache_key]

        if target_file.exists():
            px = QPixmap(str(target_file))
            if not px.isNull():
                self._pixmap_cache[cache_key] = px
                return px

        return None
