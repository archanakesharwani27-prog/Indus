"""
WakeWordDetector - Wake word detection using Porcupine (Picovoice)
"""

import os
import struct
from typing import List, Optional, Callable
import pvporcupine
import sounddevice as sd
import numpy as np


class WakeWordDetector:
    """Wake word detector using Porcupine."""
    
    def __init__(
        self,
        access_key: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        sensitivities: Optional[List[float]] = None,
        on_detected: Optional[Callable[[str], None]] = None,
    ):
        """
        Initialize wake word detector.
        
        Args:
            access_key: Picovoice access key (get from console.picovoice.ai)
            keywords: List of wake words (built-in or custom .ppn files)
            sensitivities: Sensitivity for each keyword (0.0 to 1.0)
            on_detected: Callback function(keyword) when wake word detected
        """
        self.access_key = access_key or os.getenv("PICOVOICE_ACCESS_KEY")
        if not self.access_key:
            raise ValueError(
                "PICOVOICE_ACCESS_KEY required. Get free key from console.picovoice.ai"
            )
        
        # Default keywords (built-in)
        self.keywords = keywords or ["jarvis", "hey google", "hey siri"]
        
        # Map common names to Porcupine built-in keywords
        keyword_map = {
            "hey indus": "jarvis",  # Using jarvis as closest built-in
            "indus": "jarvis",
            "jarvis": "jarvis",
            "hey jarvis": "jarvis",
        }
        
        self.porcupine_keywords = [keyword_map.get(k.lower(), k) for k in self.keywords]
        
        self.sensitivities = sensitivities or [0.5] * len(self.porcupine_keywords)
        self.on_detected = on_detected
        
        self._porcupine = None
        self._stream = None
        self._running = False
    
    def start(self) -> None:
        """Start listening for wake words."""
        if self._running:
            return
        
        self._porcupine = pvporcupine.create(
            access_key=self.access_key,
            keywords=self.porcupine_keywords,
            sensitivities=self.sensitivities,
        )
        
        self._stream = sd.InputStream(
            samplerate=self._porcupine.sample_rate,
            channels=1,
            dtype='int16',
            blocksize=self._porcupine.frame_length,
            callback=self._audio_callback,
        )
        
        self._stream.start()
        self._running = True
        print(f"Wake word detector started. Listening for: {self.keywords}")
    
    def stop(self) -> None:
        """Stop listening."""
        if not self._running:
            return
        
        self._running = False
        
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        
        if self._porcupine:
            self._porcupine.delete()
            self._porcupine = None
        
        print("Wake word detector stopped")
    
    def _audio_callback(self, indata, frames, time, status) -> None:
        """Audio callback for processing frames."""
        if not self._running or not self._porcupine:
            return
        
        # Convert to int16 array
        pcm = indata[:, 0].astype(np.int16)
        
        # Process with Porcupine
        keyword_index = self._porcupine.process(pcm)
        
        if keyword_index >= 0:
            detected_keyword = self.keywords[keyword_index]
            print(f"Wake word detected: {detected_keyword}")
            
            if self.on_detected:
                self.on_detected(detected_keyword)
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


class SimpleWakeWordDetector:
    """Simple wake word detector using keyword spotting (fallback without Porcupine)."""
    
    def __init__(self, keywords: Optional[List[str]] = None, on_detected: Optional[Callable[[str], None]] = None):
        self.keywords = [k.lower() for k in (keywords or ["hey indus", "jarvis", "indus"])]
        self.on_detected = on_detected
        self._running = False
    
    def start(self) -> None:
        """Start listening (simulated - for testing without Porcupine)."""
        self._running = True
        print(f"Simple wake word detector started (simulated). Keywords: {self.keywords}")
    
    def stop(self) -> None:
        """Stop listening."""
        self._running = False
        print("Simple wake word detector stopped")
    
    def simulate_detection(self, keyword: str) -> None:
        """Simulate wake word detection for testing."""
        if keyword.lower() in self.keywords and self.on_detected:
            self.on_detected(keyword)