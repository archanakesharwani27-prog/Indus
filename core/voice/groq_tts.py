"""
TTS Client - Groq TTS (PlayAI) with Edge TTS fallback
"""

import os
import tempfile
import asyncio
import requests
from typing import Optional

try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False


GROQ_TTS_VOICES = {
    "Arista": "Arista (female, natural, expressive)",
    "Atlas": "Atlas (male, deep, confident)",
    "Basil": "Basil (male, warm, friendly)",
    "Briggs": "Briggs (male, authoritative)",
    "Calum": "Calum (male, Scottish accent)",
    "Celeste": "Celeste (female, soft, gentle)",
    "Cheyenne": "Cheyenne (female, energetic)",
    "Chip": "Chip (male, upbeat)",
    "Cillian": "Cillian (male, Irish accent)",
    "Dede": "Dede (female, warm)",
    "Deedee": "Deedee (female, playful)",
    "Fritz": "Fritz (male, German accent)",
    "Gail": "Gail (female, professional)",
    "Indigo": "Indigo (female, mysterious)",
    "Mamaw": "Mamaw (female, grandmotherly)",
    "Mason": "Mason (male, conversational)",
    "Mikail": "Mikail (male, Middle Eastern accent)",
    "Mitch": "Mitch (male, casual)",
    "Mits": "Mits (female, Japanese accent)",
    "Nia": "Nia (female, African accent)",
    "Peyton": "Peyton (male, neutral)",
    "Pierce": "Pierce (male, deep)",
    "Quinn": "Quinn (female, bright)",
    "Reggie": "Reggie (male, friendly)",
    "Renee": "Renee (female, French accent)",
    "Rosalind": "Rosalind (female, British, elegant)",
    "Ruth": "Ruth (female, warm)",
    "Sasha": "Sasha (female, Russian accent)",
    "Skylar": "Skylar (female, airy)",
    "Stella": "Stella (female, clear)",
    "Tara": "Tara (female, Indian accent)",
    "Troy": "Troy (male, deep)",
    "Vince": "Vince (male, Italian accent)",
}

EDGE_VOICES = {
    "en-US-AriaNeural": "Aria (US, female, natural)",
    "en-US-GuyNeural": "Guy (US, male, natural)",
    "en-US-JennyNeural": "Jenny (US, female, conversational)",
    "en-US-DavisNeural": "Davis (US, male, conversational)",
    "en-GB-SoniaNeural": "Sonia (UK, female, natural)",
    "en-GB-RyanNeural": "Ryan (UK, male, natural)",
    "en-IN-NeerjaNeural": "Neerja (India, female, natural)",
    "en-IN-PrabhatNeural": "Prabhat (India, male, natural)",
    "hi-IN-SwaraNeural": "Swara (Hindi, female)",
    "hi-IN-MadhurNeural": "Madhur (Hindi, male)",
}


class TTSClient:
    """TTS client with Groq (PlayAI) primary, Edge TTS fallback."""
    
    def __init__(
        self,
        backend: str = "auto",
        voice: str = "Arista",
        rate: str = "+0%",
        volume: str = "+0%",
        groq_api_key: Optional[str] = None,
    ):
        self.backend = backend
        self.voice = voice
        self.rate = rate
        self.volume = volume
        self.groq_api_key = groq_api_key or os.getenv("GROQ_API_KEY")
        self._groq_url = "https://api.groq.com/openai/v1/audio/speech"
        self._use_fallback = False
        self._init_backend()
    
    def _init_backend(self):
        if self.backend == "auto":
            if self.groq_api_key:
                self.backend = "groq"
                print(f"[TTS] Using Groq TTS (voice: {self.voice})")
            elif EDGE_TTS_AVAILABLE:
                self.backend = "edge"
                # Map Groq voice names to Edge voices
                edge_voice = self._map_voice_to_edge(self.voice)
                self.voice = edge_voice
                print(f"[TTS] Using Edge TTS (voice: {self.voice})")
            else:
                raise RuntimeError("No TTS backend. Set GROQ_API_KEY or install edge-tts")
        elif self.backend == "groq":
            if not self.groq_api_key:
                raise RuntimeError("Groq TTS requires GROQ_API_KEY")
        elif self.backend == "edge":
            if not EDGE_TTS_AVAILABLE:
                raise RuntimeError("Edge TTS not installed: pip install edge-tts")
        else:
            raise ValueError(f"Unknown backend: {self.backend}")
    
    def _map_voice_to_edge(self, groq_voice: str) -> str:
        mapping = {
            "Arista": "en-US-AriaNeural",
            "Atlas": "en-US-GuyNeural",
            "Celeste": "en-US-JennyNeural",
            "Basil": "en-US-DavisNeural",
            "Tara": "en-IN-NeerjaNeural",
            "Mason": "en-US-GuyNeural",
        }
        return mapping.get(groq_voice, "en-US-AriaNeural")
    
    def speak(self, text: str, blocking: bool = True) -> None:
        if not text or not text.strip():
            return
        
        print(f"[TTS] ({self.backend}) Speaking: {text[:80]}...")
        
        if self.backend == "groq":
            self._speak_groq(text, blocking)
        elif self.backend == "edge":
            self._speak_edge(text, blocking)
    
    def _speak_groq(self, text: str, blocking: bool = True) -> None:
        headers = {
            "Authorization": f"Bearer {self.groq_api_key}",
            "Content-Type": "application/json",
        }
        data = {
            "model": "playai-tts",
            "voice": self.voice,
            "input": text,
            "response_format": "mp3",
        }
        
        try:
            response = requests.post(self._groq_url, json=data, headers=headers, timeout=30)
            if response.status_code == 401:
                print("[TTS] Groq TTS unauthorized, falling back to Edge TTS...")
                self._fallback_to_edge(text, blocking)
                return
            response.raise_for_status()
            audio_data = response.content
            
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                tmp.write(audio_data)
                tmp_path = tmp.name
            
            self._play_audio_file(tmp_path, blocking)
            
        except Exception as e:
            print(f"[TTS] Groq error: {e}")
            if EDGE_TTS_AVAILABLE:
                self._fallback_to_edge(text, blocking)
    
    def _fallback_to_edge(self, text: str, blocking: bool = True) -> None:
        self.backend = "edge"
        self.voice = self._map_voice_to_edge(self.voice)
        print(f"[TTS] Switched to Edge TTS (voice: {self.voice})")
        self._speak_edge(text, blocking)
    
    def _speak_edge(self, text: str, blocking: bool = True) -> None:
        async def _speak():
            communicate = edge_tts.Communicate(text, self.voice, rate=self.rate, volume=self.volume)
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                tmp_path = tmp.name
            try:
                await communicate.save(tmp_path)
                self._play_audio_file(tmp_path, blocking)
            finally:
                pass
        
        try:
            asyncio.run(_speak())
        except RuntimeError:
            loop = asyncio.new_event_loop()
            loop.run_until_complete(_speak())
            loop.close()
    
    def _play_audio_file(self, file_path: str, blocking: bool = True) -> None:
        try:
            import pygame
            pygame.mixer.init()
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()
            if blocking:
                while pygame.mixer.music.get_busy():
                    pygame.time.Clock().tick(10)
        except ImportError:
            import subprocess
            subprocess.run(["start", "", file_path], shell=True, check=False)
    
    def set_voice(self, voice: str) -> bool:
        if voice in GROQ_TTS_VOICES or voice in EDGE_VOICES:
            self.voice = voice
            return True
        return False
    
    def list_voices(self) -> list:
        if self.backend == "groq":
            return [{"id": k, "name": v} for k, v in GROQ_TTS_VOICES.items()]
        return [{"id": k, "name": v} for k, v in EDGE_VOICES.items()]


def create_tts_client(backend: str = "auto", **kwargs) -> TTSClient:
    return TTSClient(backend=backend, **kwargs)