# actions/wake_word.py
"""
INDUS / JARVIS Wake Word & Activation Controller
Provides lightweight local wake-word detection ("INDUS", "Hey INDUS", "Jarvis"),
inactivity timeout management, and seamless single-mic stream integration.
"""

import collections
import logging
import re
import threading
import time
from typing import Callable, List, Optional

logger = logging.getLogger("IndusWakeWord")

# Target activation keywords and variants
WAKE_WORDS = [
    "indus", "hey indus", "hi indus", "hello indus", "ok indus",
    "jarvis", "hey jarvis", "hi jarvis", "hello jarvis", "ok jarvis"
]
_COMPILED_WAKE_PATTERNS = [
    re.compile(rf"\b{re.escape(w)}\b", re.IGNORECASE) for w in WAKE_WORDS
]

# Standby sleep voice commands
STANDBY_COMMANDS = [
    r"\bstandby\b",
    r"\bgo\s*to\s*sleep\b",
    r"\bsleep\b",
    r"\bshant\s*ho\s*jao\b",
    r"\bso\s*jao\b",
    r"\bidle\b",
]
_COMPILED_STANDBY_PATTERNS = [re.compile(p, re.IGNORECASE) for p in STANDBY_COMMANDS]


def is_standby_phrase(text: str) -> bool:
    """Check if user explicitly told the assistant to go to sleep / standby."""
    if not text:
        return False
    t = text.strip().lower()
    return any(p.search(t) for p in _COMPILED_STANDBY_PATTERNS)


def matches_wake_word(text: str) -> Optional[str]:
    """Check if recognized text contains any wake word variant."""
    if not text:
        return None
    t = text.strip().lower()
    for w, pattern in zip(WAKE_WORDS, _COMPILED_WAKE_PATTERNS):
        if pattern.search(t):
            return w
    return None


class WakeWordController:
    """
    Manages active vs standby voice states, audio buffering, local speech recognition,
    and automatic inactivity timeouts without creating competing microphone streams.
    """

    def __init__(
        self,
        inactivity_timeout: float = 8.0,
        sample_rate: int = 16000,
        on_activate: Optional[Callable[[str, bytes], None]] = None,
        on_deactivate: Optional[Callable[[str], None]] = None,
    ):
        self.inactivity_timeout = inactivity_timeout
        self.sample_rate = sample_rate
        self.on_activate = on_activate
        self.on_deactivate = on_deactivate

        self._is_active = False
        self._lock = threading.Lock()
        self._last_active_time = 0.0

        # Audio sliding buffer for standby wake-word recognition (approx 2.0s)
        self._buffer_chunks = collections.deque(maxlen=32)  # 32 * ~64ms = ~2.048s
        self._recognizing = False
        self._energy_trigger_count = 0

        # SpeechRecognition instance for offline buffer decoding
        self._sr_recognizer = None
        try:
            import speech_recognition as sr
            self._sr_recognizer = sr.Recognizer()
            self._sr_recognizer.energy_threshold = 300
            self._sr_recognizer.dynamic_energy_threshold = False
        except ImportError:
            self._sr_recognizer = None

    @property
    def is_active(self) -> bool:
        with self._lock:
            return self._is_active

    @property
    def state(self) -> str:
        with self._lock:
            return "ACTIVE" if self._is_active else "STANDBY"


    def activate(self, source: str = "wake_word", buffered_audio: bytes = b""):
        """Transition from STANDBY to ACTIVE."""
        with self._lock:
            was_active = self._is_active
            self._is_active = True
            self._last_active_time = time.time()
            self._buffer_chunks.clear()

        print(f"[WakeWord] Activated (Source: '{source}')")
        if not was_active and self.on_activate:
            try:
                self.on_activate(source, buffered_audio)
            except Exception as e:
                print(f"[WakeWord] on_activate error: {e}")

    def deactivate(self, reason: str = "inactivity_timeout"):
        """Transition from ACTIVE to STANDBY."""
        with self._lock:
            was_active = self._is_active
            self._is_active = False
            self._buffer_chunks.clear()

        print(f"[WakeWord] Returned to STANDBY (Reason: '{reason}')")
        if was_active and self.on_deactivate:
            try:
                self.on_deactivate(reason)
            except Exception as e:
                print(f"[WakeWord] on_deactivate error: {e}")

    def touch(self):
        """Reset the inactivity timer during active conversations or tool executions."""
        with self._lock:
            if self._is_active:
                self._last_active_time = time.time()

    def check_inactivity(self):
        """Called periodically to check if inactivity timeout has elapsed."""
        with self._lock:
            if not self._is_active:
                return
            elapsed = time.time() - self._last_active_time
            should_deactivate = elapsed >= self.inactivity_timeout

        if should_deactivate:
            self.deactivate(reason=f"Inactivity timeout ({self.inactivity_timeout:.0f}s elapsed)")

    def feed_audio(self, pcm_bytes: bytes, rms: float) -> bool:
        """
        Process a PCM 16kHz chunk from the microphone stream.
        Returns True if the chunk should be forwarded to Gemini Live (when ACTIVE),
        or False if in STANDBY (audio is held locally for wake word detection).
        """
        with self._lock:
            active = self._is_active

        if active:
            # When active, update activity timestamp only on real voice energy (> 100 rms)
            if rms > 100.0:
                self.touch()
            return True

        # In STANDBY mode: Buffer audio chunks for wake word scanning
        self._buffer_chunks.append(pcm_bytes)

        if rms > 45.0:
            self._energy_trigger_count += 1
        else:
            self._energy_trigger_count = max(0, self._energy_trigger_count - 1)

        # Trigger recognition when voice activity is detected and not already scanning
        if self._energy_trigger_count >= 3 and not self._recognizing:
            self._recognizing = True
            threading.Thread(target=self._scan_buffer_for_wake_word, daemon=True).start()

        return False

    def _scan_buffer_for_wake_word(self):
        """Decode buffered PCM audio in background to check for wake words."""
        try:
            time.sleep(0.35)  # Allow a few trailing syllables to arrive
            with self._lock:
                chunks = list(self._buffer_chunks)
            if not chunks:
                return

            pcm_combined = b"".join(chunks)

            text = self.recognize_audio_buffer(pcm_combined)
            if text:
                matched = matches_wake_word(text)
                if matched:
                    print(f"[WakeWord] [!] Wake phrase matched: '{matched}' (Heard: '{text}')")
                    self.activate(source=matched, buffered_audio=pcm_combined)
        except Exception as e:
            logger.debug(f"Wake word scan error: {e}")
        finally:
            self._recognizing = False
            self._energy_trigger_count = 0

    def recognize_audio_buffer(self, pcm_bytes: bytes) -> Optional[str]:
        """Convert PCM 16kHz audio buffer into text using local Recognizer."""
        if not self._sr_recognizer or len(pcm_bytes) < 8000:
            return None
        try:
            import speech_recognition as sr
            audio_data = sr.AudioData(pcm_bytes, self.sample_rate, 2)
            # Use Google Speech or local recognizer
            text = self._sr_recognizer.recognize_google(audio_data, language="en-IN").lower()
            return text
        except Exception:
            return None


# Global singleton instance
wake_word_controller = WakeWordController()
