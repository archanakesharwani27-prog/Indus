"""
AudioStream - Audio input/output handling for voice interaction
"""

import sounddevice as sd
import numpy as np
import wave
import tempfile
import os
import threading
import queue
from typing import Optional, Callable, Generator
from dataclasses import dataclass


@dataclass
class AudioConfig:
    """Audio configuration."""
    sample_rate: int = 16000
    channels: int = 1
    dtype: str = 'int16'
    block_size: int = 1024
    silence_threshold: float = 0.01
    max_silence_seconds: float = 2.0
    max_recording_seconds: float = 30.0


class AudioStream:
    """Audio input/output stream handler."""
    
    def __init__(self, config: Optional[AudioConfig] = None):
        self.config = config or AudioConfig()
        self._stream = None
        self._recording = False
        self._audio_queue = queue.Queue()
        self._callback = None
    
    def list_devices(self) -> list:
        """List available audio devices."""
        return sd.query_devices()
    
    def get_default_input_device(self) -> dict:
        """Get default input device info."""
        return sd.query_devices(kind='input')
    
    def get_default_output_device(self) -> dict:
        """Get default output device info."""
        return sd.query_devices(kind='output')
    
    def record(self, duration: Optional[float] = None) -> bytes:
        """
        Record audio for specified duration.
        
        Args:
            duration: Recording duration in seconds (None = use config max)
            
        Returns:
            Audio data as WAV bytes
        """
        duration = duration or self.config.max_recording_seconds
        frames = int(duration * self.config.sample_rate)
        
        print(f"Recording for {duration}s...")
        recording = sd.rec(
            frames,
            samplerate=self.config.sample_rate,
            channels=self.config.channels,
            dtype=self.config.dtype,
        )
        sd.wait()
        print("Recording complete")
        
        return self._numpy_to_wav(recording)
    
    def record_until_silence(
        self,
        silence_threshold: Optional[float] = None,
        max_silence_seconds: Optional[float] = None,
        max_duration: Optional[float] = None,
    ) -> bytes:
        """
        Record until silence detected (voice activity detection).
        
        Args:
            silence_threshold: RMS threshold for silence detection
            max_silence_seconds: Max silence before stopping
            max_duration: Maximum recording duration
            
        Returns:
            Audio data as WAV bytes
        """
        silence_threshold = silence_threshold or self.config.silence_threshold
        max_silence_seconds = max_silence_seconds or self.config.max_silence_seconds
        max_duration = max_duration or self.config.max_recording_seconds
        
        silence_frames = int(max_silence_seconds * self.config.sample_rate / self.config.block_size)
        max_frames = int(max_duration * self.config.sample_rate / self.config.block_size)
        
        frames_recorded = 0
        silent_frames = 0
        recording = []
        
        print("Listening... (speak now)")
        
        def callback(indata, frames, time, status):
            nonlocal frames_recorded, silent_frames
            
            if status:
                print(f"Audio status: {status}")
            
            # Calculate RMS energy
            rms = np.sqrt(np.mean(indata.astype(np.float32) ** 2))
            normalized_rms = rms / 32768.0  # Normalize for int16
            
            recording.append(indata.copy())
            frames_recorded += 1
            
            if normalized_rms < silence_threshold:
                silent_frames += 1
            else:
                silent_frames = 0
            
            # Check stop conditions
            if silent_frames >= silence_frames:
                raise sd.CallbackStop("Silence detected")
            if frames_recorded >= max_frames:
                raise sd.CallbackStop("Max duration reached")
        
        try:
            with sd.InputStream(
                samplerate=self.config.sample_rate,
                channels=self.config.channels,
                dtype=self.config.dtype,
                blocksize=self.config.block_size,
                callback=callback,
            ):
                sd.sleep(int(max_duration * 1000))
        except sd.CallbackStop as e:
            print(f"Recording stopped: {e}")
        
        if not recording:
            return b""
        
        audio_data = np.concatenate(recording, axis=0)
        print(f"Recorded {len(audio_data) / self.config.sample_rate:.1f}s of audio")
        
        return self._numpy_to_wav(audio_data)
    
    def _numpy_to_wav(self, audio_data: np.ndarray) -> bytes:
        """Convert numpy array to WAV bytes."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            with wave.open(tmp_path, 'wb') as wav_file:
                wav_file.setnchannels(self.config.channels)
                wav_file.setsampwidth(2)  # 16-bit = 2 bytes
                wav_file.setframerate(self.config.sample_rate)
                wav_file.writeframes(audio_data.tobytes())
            
            with open(tmp_path, 'rb') as f:
                return f.read()
        finally:
            try:
                os.unlink(tmp_path)
            except:
                pass
    
    def play_wav(self, wav_data: bytes, blocking: bool = True) -> None:
        """Play WAV audio data."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(wav_data)
            tmp_path = tmp.name
        
        try:
            import pygame
            pygame.mixer.init()
            pygame.mixer.music.load(tmp_path)
            pygame.mixer.music.play()
            
            if blocking:
                while pygame.mixer.music.get_busy():
                    pygame.time.Clock().tick(10)
        except ImportError:
            import subprocess
            subprocess.run(["start", "", tmp_path], shell=True, check=False)
        finally:
            try:
                os.unlink(tmp_path)
            except:
                pass
    
    def play_bytes(self, audio_data: bytes, blocking: bool = True) -> None:
        """Play raw audio bytes (assumes MP3 from TTS)."""
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp.write(audio_data)
            tmp_path = tmp.name
        
        try:
            import pygame
            pygame.mixer.init()
            pygame.mixer.music.load(tmp_path)
            pygame.mixer.music.play()
            
            if blocking:
                while pygame.mixer.music.get_busy():
                    pygame.time.Clock().tick(10)
        except ImportError:
            import subprocess
            subprocess.run(["start", "", tmp_path], shell=True, check=False)
        finally:
            try:
                os.unlink(tmp_path)
            except:
                pass


class StreamingAudioInput:
    """Streaming audio input for real-time processing."""
    
    def __init__(self, config: Optional[AudioConfig] = None):
        self.config = config or AudioConfig()
        self._stream = None
        self._buffer = queue.Queue()
        self._running = False
    
    def start(self) -> None:
        """Start streaming input."""
        if self._running:
            return
        
        self._running = True
        
        def callback(indata, frames, time, status):
            if status:
                print(f"Stream status: {status}")
            self._buffer.put(indata.copy())
        
        self._stream = sd.InputStream(
            samplerate=self.config.sample_rate,
            channels=self.config.channels,
            dtype=self.config.dtype,
            blocksize=self.config.block_size,
            callback=callback,
        )
        self._stream.start()
    
    def stop(self) -> None:
        """Stop streaming input."""
        if not self._running:
            return
        
        self._running = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
    
    def get_chunk(self, timeout: float = 1.0) -> Optional[np.ndarray]:
        """Get next audio chunk."""
        try:
            return self._buffer.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def __iter__(self) -> Generator[np.ndarray, None, None]:
        """Iterate over audio chunks."""
        while self._running:
            chunk = self.get_chunk()
            if chunk is not None:
                yield chunk