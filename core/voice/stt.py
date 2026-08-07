"""
WhisperClient - Speech-to-Text using OpenAI Whisper API
"""

import os
import io
import wave
import tempfile
from typing import Optional, BinaryIO
from openai import OpenAI


class WhisperClient:
    """OpenAI Whisper API client for speech-to-text."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "whisper-1"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY required for WhisperClient")
        self.client = OpenAI(api_key=self.api_key)
        self.model = model
    
    def transcribe(self, audio_data: bytes, language: Optional[str] = None) -> str:
        """
        Transcribe audio bytes to text.
        
        Args:
            audio_data: Raw audio bytes (WAV format preferred)
            language: Optional language code (e.g., 'en', 'hi')
            
        Returns:
            Transcribed text
        """
        # Create a temporary WAV file for the API
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_data)
            tmp_path = tmp.name
        
        try:
            with open(tmp_path, "rb") as audio_file:
                kwargs = {"model": self.model, "file": audio_file}
                if language:
                    kwargs["language"] = language
                
                response = self.client.audio.transcriptions.create(**kwargs)
                return response.text.strip()
        finally:
            os.unlink(tmp_path)
    
    def transcribe_file(self, file_path: str, language: Optional[str] = None) -> str:
        """Transcribe audio from a file path."""
        with open(file_path, "rb") as f:
            audio_data = f.read()
        return self.transcribe(audio_data, language)
    
    def transcribe_stream(self, audio_stream: BinaryIO, language: Optional[str] = None) -> str:
        """Transcribe from a file-like object."""
        audio_data = audio_stream.read()
        return self.transcribe(audio_data, language)


class StreamingWhisperClient:
    """Streaming Whisper client for real-time transcription (future enhancement)."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "whisper-1"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY required")
        self.client = OpenAI(api_key=self.api_key)
        self.model = model
    
    def transcribe_chunk(self, audio_chunk: bytes) -> str:
        """Transcribe a single audio chunk (not fully streaming yet)."""
        return WhisperClient(self.api_key, self.model).transcribe(audio_chunk)