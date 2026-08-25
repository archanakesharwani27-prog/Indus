# core/avatar/viseme.py
"""
INDUS Avatar System -- Phoneme-to-Viseme Engine
Converts spoken text into a timed sequence of mouth shapes (visemes)
synchronized with audio playback. Supports English + Hinglish.
"""

import re
import threading
from typing import List, Tuple
from dataclasses import dataclass
from core.avatar.models import VisemeShape

# ── Grapheme-to-Viseme rules (digraphs first, then single chars) ────────────
_RULES: List[Tuple[str, VisemeShape]] = [
    # Digraphs
    ("ph", VisemeShape.LABIODENTAL),
    ("th", VisemeShape.DENTAL),
    ("sh", VisemeShape.PALATAL),
    ("ch", VisemeShape.PALATAL),
    ("zh", VisemeShape.PALATAL),
    ("wh", VisemeShape.LABROUND),
    ("ng", VisemeShape.VELAR),
    ("nk", VisemeShape.VELAR),
    ("ck", VisemeShape.VELAR),
    ("gh", VisemeShape.VELAR),
    ("kh", VisemeShape.VELAR),
    ("aa", VisemeShape.VOWEL_OPEN),
    ("ai", VisemeShape.VOWEL_MID),
    ("au", VisemeShape.VOWEL_OPEN),
    ("ae", VisemeShape.VOWEL_MID),
    ("ee", VisemeShape.VOWEL_HIGH),
    ("ea", VisemeShape.VOWEL_HIGH),
    ("oo", VisemeShape.VOWEL_TIGHT),
    ("ou", VisemeShape.VOWEL_ROUND),
    ("ow", VisemeShape.VOWEL_ROUND),
    ("oi", VisemeShape.VOWEL_ROUND),
    ("ey", VisemeShape.VOWEL_MID),
    ("ay", VisemeShape.VOWEL_MID),
    ("aw", VisemeShape.VOWEL_OPEN),
    ("rr", VisemeShape.GLIDE),
    ("tt", VisemeShape.ALVEOLAR),
    ("dd", VisemeShape.ALVEOLAR),
    ("ss", VisemeShape.ALVEOLAR),
    ("ll", VisemeShape.ALVEOLAR),
    ("nn", VisemeShape.ALVEOLAR),
    # Single vowels
    ("a",  VisemeShape.VOWEL_OPEN),
    ("e",  VisemeShape.VOWEL_MID),
    ("i",  VisemeShape.VOWEL_HIGH),
    ("o",  VisemeShape.VOWEL_ROUND),
    ("u",  VisemeShape.VOWEL_TIGHT),
    # Single consonants
    ("b",  VisemeShape.BILABIAL),
    ("p",  VisemeShape.BILABIAL),
    ("m",  VisemeShape.BILABIAL),
    ("f",  VisemeShape.LABIODENTAL),
    ("v",  VisemeShape.LABIODENTAL),
    ("w",  VisemeShape.LABROUND),
    ("t",  VisemeShape.ALVEOLAR),
    ("d",  VisemeShape.ALVEOLAR),
    ("s",  VisemeShape.ALVEOLAR),
    ("z",  VisemeShape.ALVEOLAR),
    ("n",  VisemeShape.ALVEOLAR),
    ("l",  VisemeShape.ALVEOLAR),
    ("r",  VisemeShape.GLIDE),
    ("y",  VisemeShape.GLIDE),
    ("j",  VisemeShape.PALATAL),
    ("x",  VisemeShape.ALVEOLAR),
    ("k",  VisemeShape.VELAR),
    ("g",  VisemeShape.VELAR),
    ("q",  VisemeShape.VELAR),
    ("c",  VisemeShape.VELAR),
    ("h",  VisemeShape.SCHWA),
]

# Duration per viseme in ms (normal speech rate ~150 wpm)
_DUR: dict = {
    VisemeShape.SILENCE:     180,
    VisemeShape.BILABIAL:    70,
    VisemeShape.LABIODENTAL: 75,
    VisemeShape.DENTAL:      85,
    VisemeShape.ALVEOLAR:    70,
    VisemeShape.PALATAL:     80,
    VisemeShape.VELAR:       70,
    VisemeShape.VOWEL_OPEN:  140,
    VisemeShape.VOWEL_MID:   120,
    VisemeShape.VOWEL_HIGH:  110,
    VisemeShape.VOWEL_ROUND: 130,
    VisemeShape.VOWEL_TIGHT: 115,
    VisemeShape.SCHWA:       90,
    VisemeShape.LABROUND:    100,
    VisemeShape.GLIDE:       85,
}

# Mouth openness per viseme (0.0–1.0)
_OPEN: dict = {
    VisemeShape.SILENCE:     0.00,
    VisemeShape.BILABIAL:    0.00,
    VisemeShape.LABIODENTAL: 0.15,
    VisemeShape.DENTAL:      0.22,
    VisemeShape.ALVEOLAR:    0.28,
    VisemeShape.PALATAL:     0.38,
    VisemeShape.VELAR:       0.32,
    VisemeShape.VOWEL_OPEN:  0.92,
    VisemeShape.VOWEL_MID:   0.58,
    VisemeShape.VOWEL_HIGH:  0.38,
    VisemeShape.VOWEL_ROUND: 0.65,
    VisemeShape.VOWEL_TIGHT: 0.48,
    VisemeShape.SCHWA:       0.32,
    VisemeShape.LABROUND:    0.42,
    VisemeShape.GLIDE:       0.25,
}

# Lip spread: -1.0 = very round/pursed, 0 = neutral, +1.0 = wide horizontal stretch
_SPREAD: dict = {
    VisemeShape.SILENCE:      0.0,
    VisemeShape.BILABIAL:     0.0,
    VisemeShape.LABIODENTAL:  0.2,
    VisemeShape.DENTAL:       0.1,
    VisemeShape.ALVEOLAR:     0.3,
    VisemeShape.PALATAL:     -0.3,
    VisemeShape.VELAR:        0.1,
    VisemeShape.VOWEL_OPEN:   0.4,
    VisemeShape.VOWEL_MID:    0.7,   # E — wide horizontal
    VisemeShape.VOWEL_HIGH:   0.8,   # I — widest
    VisemeShape.VOWEL_ROUND: -0.5,   # O — rounded
    VisemeShape.VOWEL_TIGHT: -0.8,   # OO — very rounded
    VisemeShape.SCHWA:        0.1,
    VisemeShape.LABROUND:    -0.6,
    VisemeShape.GLIDE:        0.0,
}

_EMOJI_STRIP = re.compile(
    "[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF"
    "\U00002600-\U000027BF\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF]+",
    flags=re.UNICODE
)


@dataclass
class VisemeFrame:
    viseme:      VisemeShape
    duration_ms: float   # ms to hold this shape
    openness:    float   # 0.0–1.0
    spread:      float   # -1.0 round … +1.0 horizontal stretch


def text_to_viseme_frames(text: str, speech_rate: float = 1.0) -> List[VisemeFrame]:
    """
    Convert spoken text → ordered list of VisemeFrames with timing.
    Handles English + Hinglish Roman transliteration.
    speech_rate: 1.0=normal, 0.8=slow, 1.2=fast
    """
    if not text:
        return []

    clean = _EMOJI_STRIP.sub('', text)
    clean = re.sub(r'[^\x00-\x7F]', '', clean)
    clean = re.sub(r'[^\w\s\'-]', ' ', clean).lower()

    frames: List[VisemeFrame] = []
    words = clean.split()

    for w_idx, word in enumerate(words):
        if w_idx > 0:
            frames.append(VisemeFrame(
                viseme=VisemeShape.SILENCE,
                duration_ms=_DUR[VisemeShape.SILENCE] * 0.25 / speech_rate,
                openness=0.0, spread=0.0
            ))

        i = 0
        while i < len(word):
            matched = False
            for pattern_len in (2, 1):
                if i + pattern_len > len(word):
                    continue
                chunk = word[i:i + pattern_len]
                for grapheme, viseme in _RULES:
                    if grapheme == chunk:
                        frames.append(VisemeFrame(
                            viseme=viseme,
                            duration_ms=_DUR[viseme] / speech_rate,
                            openness=_OPEN[viseme],
                            spread=_SPREAD[viseme],
                        ))
                        i += pattern_len
                        matched = True
                        break
                if matched:
                    break
            if not matched:
                i += 1

    return frames


class VisemeTimeline:
    """
    Thread-safe real-time playback of a VisemeFrame sequence.
    advance(dt_ms) steps forward and returns current mouth state.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._frames: List[VisemeFrame] = []
        self._idx: int = 0
        self._elapsed_ms: float = 0.0
        self._current = VisemeShape.SILENCE
        self._openness = 0.0
        self._spread = 0.0

    def load(self, frames: List[VisemeFrame]):
        """Replace current sequence."""
        with self._lock:
            self._frames = frames[:]
            self._idx = 0
            self._elapsed_ms = 0.0

    def append(self, frames: List[VisemeFrame]):
        """Stream more frames onto the end (for incremental text)."""
        with self._lock:
            self._frames.extend(frames)

    def advance(self, dt_ms: float) -> tuple:
        """Step dt_ms forward. Returns (VisemeShape, openness, spread)."""
        with self._lock:
            if not self._frames or self._idx >= len(self._frames):
                self._current = VisemeShape.SILENCE
                self._openness = 0.0
                self._spread = 0.0
                return self._current, self._openness, self._spread

            self._elapsed_ms += dt_ms
            while (self._idx < len(self._frames) and
                   self._elapsed_ms >= self._frames[self._idx].duration_ms):
                self._elapsed_ms -= self._frames[self._idx].duration_ms
                self._idx += 1

            if self._idx < len(self._frames):
                f = self._frames[self._idx]
                self._current = f.viseme
                self._openness = f.openness
                self._spread = f.spread
            else:
                self._current = VisemeShape.SILENCE
                self._openness = 0.0
                self._spread = 0.0

            return self._current, self._openness, self._spread

    def reset(self):
        with self._lock:
            self._frames.clear()
            self._idx = 0
            self._elapsed_ms = 0.0
            self._current = VisemeShape.SILENCE
            self._openness = 0.0
            self._spread = 0.0

    @property
    def is_active(self) -> bool:
        with self._lock:
            return bool(self._frames) and self._idx < len(self._frames)

    @property
    def current_viseme(self) -> VisemeShape:
        return self._current

    @property
    def current_openness(self) -> float:
        return self._openness

    @property
    def current_spread(self) -> float:
        return self._spread
