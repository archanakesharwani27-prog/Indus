"""
Phase 2 Integration Tests - Voice (Wake Word, STT, TTS)
Tests voice components with real APIs.
Run: python -m pytest tests/test_integration_phase2.py -v -s
"""

import os
import sys
import pytest
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope="module")
def audio_config():
    from core.voice.audio_io import AudioConfig
    return AudioConfig()


def test_audio_devices_available(audio_config):
    """Test audio input/output devices are available."""
    import pyaudio
    p = pyaudio.PyAudio()
    
    input_devices = []
    output_devices = []
    
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        if info["maxInputChannels"] > 0:
            input_devices.append((i, info["name"]))
        if info["maxOutputChannels"] > 0:
            output_devices.append((i, info["name"]))
    
    p.terminate()
    
    print(f"\nInput devices: {input_devices}")
    print(f"Output devices: {output_devices}")
    
    assert len(input_devices) > 0, "No audio input devices found"
    assert len(output_devices) > 0, "No audio output devices found"


def test_audio_stream_record_playback(audio_config):
    """Test recording and playback audio stream."""
    from core.voice.audio_io import AudioStream
    import numpy as np
    
    stream = AudioStream(audio_config)
    
    # Record 2 seconds of audio
    print("\nRecording 2 seconds... (speak into mic)")
    audio_data = stream.record(duration=2.0)
    
    assert audio_data is not None, "No audio recorded"
    assert len(audio_data) > 0, "Empty audio data"
    
    # Check audio has signal (not silence)
    audio_array = np.frombuffer(audio_data, dtype=np.int16)
    max_amplitude = np.max(np.abs(audio_array))
    print(f"Recorded audio: {len(audio_data)} bytes, max amplitude: {max_amplitude}")
    
    # Playback
    print("Playing back...")
    stream.play_wav(audio_data)
    
    assert max_amplitude > 100, "Audio appears to be silent - check microphone"


def test_whisper_stt_transcription(audio_config):
    """Test Whisper STT transcription with real audio."""
    from core.voice.audio_io import AudioStream
    from core.voice.stt import WhisperClient
    
    stream = AudioStream(audio_config)
    stt = WhisperClient()
    
    print("\nRecording for STT test... (say something clearly)")
    audio_data = stream.record(duration=3.0)
    
    assert audio_data is not None, "No audio recorded"
    
    print("Transcribing...")
    text = stt.transcribe(audio_data)
    
    print(f"Transcribed: '{text}'")
    
    # Whisper should return some text (even if not perfect)
    assert isinstance(text, str)
    assert len(text) > 0, "STT returned empty text"


def test_edge_tts_synthesis():
    """Test Edge TTS synthesis (via Groq TTS fallback)."""
    from core.voice.groq_tts import TTSClient
    
    tts = TTSClient(backend="edge", voice="en-US-AriaNeural")
    
    print("\nTesting Edge TTS...")
    tts.speak("Hello, this is a test.", blocking=True)
    
    # Just verify no exception
    assert True


def test_groq_tts_synthesis():
    """Test Groq TTS synthesis (requires GROQ_API_KEY)."""
    from core.voice.groq_tts import TTSClient
    
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        pytest.skip("GROQ_API_KEY not set")
    
    tts = TTSClient(voice="Arista")
    
    print("\nTesting Groq TTS...")
    audio_data = tts.synthesize("Hello, this is a test.")
    
    assert audio_data is not None, "TTS returned no audio"
    assert len(audio_data) > 0, "TTS returned empty audio"
    
    print(f"Synthesized audio: {len(audio_data)} bytes")


def test_wake_word_detector():
    """Test simulated wake word detector."""
    from core.voice.wake_word import SimpleWakeWordDetector
    
    detected_keyword = None
    
    def on_detected(keyword):
        nonlocal detected_keyword
        detected_keyword = keyword
        print(f"\nWake word detected: {keyword}")
    
    detector = SimpleWakeWordDetector(
        keywords=["hey indus", "jarvis"],
        on_detected=on_detected,
    )
    
    print("\nTesting wake word detector (simulated)...")
    detector.start()
    
    # Simulate wake word
    import time
    time.sleep(0.5)
    detector.simulate_detection("hey indus")
    time.sleep(0.5)
    
    detector.stop()
    
    assert detected_keyword == "hey indus", f"Expected 'hey indus', got {detected_keyword}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])