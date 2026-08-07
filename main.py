"""
Indus - Personal AI Assistant. Entry point with voice mode support.
"""

import os
import sys
import argparse
import signal
from dotenv import load_dotenv

from core.memory import Memory
from core.chat_engine import ChatEngine
from core.voice.gemini_live import GeminiLiveClient
from core.voice.groq_tts import TTSClient

load_dotenv()


def get_provider():
    """.env mein PROVIDER=gemini/nvidia/mock/groq set karo. Default gemini hai."""
    provider_name = os.getenv("PROVIDER", "gemini").lower()
    persona = os.getenv("CHAT_PERSONA", "zoya")  # zoya, friendly, natural, none

    if provider_name == "mock":
        from providers.mock_provider import MockProvider
        return MockProvider(persona=persona)

    if provider_name == "gemini":
        from providers.gemini_provider import GeminiProvider
        return GeminiProvider(persona=persona)

    if provider_name == "nvidia":
        from providers.nvidia_provider import NVIDIAProvider
        return NVIDIAProvider(persona=persona)

    if provider_name == "groq":
        from providers.groq_provider import GroqProvider
        return GroqProvider(persona=persona)

    raise ValueError(f"Unknown provider: {provider_name}")


def run_text_mode(engine: ChatEngine) -> None:
    """Run in text-only mode (original behavior)."""
    print("Indus AI Assistant - Text Mode (type 'exit' to quit)")

    def signal_handler(sig, frame):
        print("\nIndus: Alright, see you later!")
        engine.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nIndus: Alright, see you later!")
            engine.shutdown()
            break

        if user_input.lower() in ("exit", "quit"):
            print("Indus: Alright, see you later!")
            engine.shutdown()
            break
        if not user_input:
            continue

        try:
            reply = engine.respond(user_input)
            print(f"Indus: {reply}\n")
        except Exception as e:
            print(f"Error: {e}\n")


def run_voice_mode(engine: ChatEngine) -> None:
    """Run in voice mode with wake word detection."""
    print("Indus AI Assistant - Voice Mode")
    print("Say 'Hey Indus' or 'Jarvis' to activate\n")

    def signal_handler(sig, frame):
        print("\nStopping...")
        engine.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        from core.voice.wake_word import WakeWordDetector, SimpleWakeWordDetector
        from core.voice.audio_io import AudioStream, AudioConfig
        from core.voice.stt import WhisperClient
    except ImportError as e:
        print(f"Voice mode unavailable: {e}")
        print("Falling back to text mode...")
        run_text_mode(engine)
        return

    # Initialize voice components
    audio_config = AudioConfig()
    audio_stream = AudioStream(audio_config)

    # Check for Picovoice access key
    has_picovoice = bool(os.getenv("PICOVOICE_ACCESS_KEY"))

    # State for voice interaction
    listening = False

    def on_wake_word(keyword: str):
        nonlocal listening
        print(f"\n[Wake word detected: {keyword}]")
        print("Listening...")
        listening = True
        process_voice_command()

    def process_voice_command():
        nonlocal listening
        try:
            # Record until silence
            audio_data = audio_stream.record_until_silence()
            
            if not audio_data:
                print("No audio recorded")
                listening = False
                return

            print("Transcribing...")
            text = stt.transcribe(audio_data)
            print(f"You: {text}")

            if not text:
                print("I didn't catch that. Please try again.")
                listening = False
                return

            # Process through engine
            reply = engine.respond(text)
            print(f"Indus: {reply}")

        except Exception as e:
            print(f"Voice error: {e}")
            print("Sorry, I had an error processing that.")
        finally:
            listening = False
            print("\nSay 'Hey Indus' or 'Jarvis' to activate")

    stt = WhisperClient()

    if has_picovoice:
        wake_detector = WakeWordDetector(
            keywords=["jarvis", "hey google"],
            on_detected=on_wake_word,
        )
    else:
        print("Note: PICOVOICE_ACCESS_KEY not set. Using simulated wake word.")
        print("Get free key from console.picovoice.ai for real wake word detection.")
        wake_detector = SimpleWakeWordDetector(
            keywords=["hey indus", "jarvis", "indus"],
            on_detected=on_wake_word,
        )

    # Start wake word detection
    wake_detector.start()

    try:
        # Keep main thread alive
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        wake_detector.stop()
        engine.shutdown()
        print("Indus: Alright, see you later!")


def run_gemini_live_mode(engine: ChatEngine) -> None:
    """Run in real-time voice mode using Gemini Live API."""
    print("Indus AI Assistant - Gemini Live Voice Mode")
    print("Real-time bidirectional voice streaming with Gemini")
    print("Press Ctrl+C to stop\n")

    def signal_handler(sig, frame):
        print("\nStopping...")
        engine.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        print("Error: GEMINI_API_KEY not set in .env")
        print("Falling back to text mode...")
        run_text_mode(engine)
        return

    voice = os.getenv("GEMINI_LIVE_VOICE", "Aoede")
    persona = os.getenv("GEMINI_LIVE_PERSONA", "zoya")
    
    # Find WO Mic device index
    import pyaudio
    p = pyaudio.PyAudio()
    wo_mic_index = None
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        if "WO Mic" in info["name"] and info["maxInputChannels"] > 0:
            # Test which one actually captures audio
            try:
                stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, input_device_index=i, frames_per_buffer=1024)
                frames = [stream.read(1024) for _ in range(8)]
                stream.stop_stream(); stream.close()
                import numpy as np
                data = np.frombuffer(b''.join(frames), dtype=np.int16)
                if np.max(np.abs(data)) > 100:
                    wo_mic_index = i
                    print(f"[Audio] Found working WO Mic at device index {i}: {info['name']} (amp={np.max(np.abs(data))})")
                    break
                else:
                    print(f"[Audio] WO Mic at index {i} is silent (amp={np.max(np.abs(data))})")
            except Exception as e:
                print(f"[Audio] WO Mic at index {i} error: {e}")
    p.terminate()
    
    if wo_mic_index is None:
        print("[Audio] Warning: No working WO Mic found, using default input device")

    try:
        # Check for proxy URL (Zoya-style architecture)
        proxy_url = os.getenv("PROXY_URL")
        if proxy_url:
            print(f"[Gemini Live] Using proxy server: {proxy_url}")
        
        live_client = GeminiLiveClient(
            api_key=gemini_api_key,
            voice=voice,
            persona=persona,
            input_device_index=wo_mic_index,
            proxy_url=proxy_url,
        )
    except Exception as e:
        print(f"Failed to initialize Gemini Live: {e}")
        print("Falling back to text mode...")
        run_text_mode(engine)
        return

    print(f"Starting Gemini Live with voice: {voice}, persona: {persona}")
    print("Speak naturally - Gemini will respond in real-time\n")
    
    try:
        live_client.run_blocking()
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        engine.shutdown()
        print("Indus: Alright, see you later!")


def main():
    parser = argparse.ArgumentParser(description="Indus AI Assistant")
    parser.add_argument(
        "--voice", "-v",
        action="store_true",
        help="Run in voice mode with wake word detection (STT + LLM)"
    )
    parser.add_argument(
        "--live-voice", "-l",
        action="store_true",
        help="Run in real-time voice mode using Gemini Live API (bidirectional streaming)"
    )
    parser.add_argument(
        "--text-voice", "-t",
        action="store_true",
        help="Run in text mode with voice output (type text, hear voice + see text)"
    )
    parser.add_argument(
        "--tts-voice",
        default="Arista",
        help="Groq TTS voice to use (default: Arista)"
    )
    parser.add_argument(
        "--persona",
        choices=["zoya", "assistant"],
        default="zoya",
        help="Voice persona for Gemini Live (default: zoya)"
    )
    parser.add_argument(
        "--provider", "-p",
        choices=["gemini", "nvidia", "mock", "groq"],
        help="LLM provider to use (overrides .env)"
    )
    args = parser.parse_args()

    # Override provider from command line
    if args.provider:
        os.environ["PROVIDER"] = args.provider
    
    # Override persona from command line
    if args.persona:
        os.environ["GEMINI_LIVE_PERSONA"] = args.persona

    try:
        provider = get_provider()
    except ValueError as e:
        print(f"Error: {e}")
        return

    # Get persona from env (default: zoya)
    persona = os.getenv("CHAT_PERSONA", "zoya")

    memory = Memory(db_path="indus.db")
    engine = ChatEngine(provider=provider, memory=memory, persona=persona)

    if args.live_voice:
        run_gemini_live_mode(engine)
    elif args.voice:
        run_voice_mode(engine)
    elif args.text_voice:
        run_text_voice_mode(engine, args.tts_voice)
    else:
        run_text_mode(engine)


def run_text_voice_mode(engine: ChatEngine, tts_voice: str = "Arista") -> None:
    """Run in text mode with voice output (type text, hear voice + see text)."""
    print("Indus AI Assistant - Text + Voice Mode (type 'exit' to quit)")
    print(f"TTS Voice: {tts_voice}\n")

    def signal_handler(sig, frame):
        print("\nIndus: Alright, see you later!")
        engine.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        tts = TTSClient(voice=tts_voice)
        print(f"[TTS] Initialized with voice: {tts_voice}")
    except Exception as e:
        print(f"[TTS] Failed to initialize: {e}")
        print("Falling back to text-only mode...")
        run_text_mode(engine)
        return

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nIndus: Alright, see you later!")
            engine.shutdown()
            break

        if user_input.lower() in ("exit", "quit"):
            print("Indus: Alright, see you later!")
            engine.shutdown()
            break
        if not user_input:
            continue

        try:
            reply = engine.respond(user_input)
            print(f"Indus: {reply}\n")
            tts.speak(reply)
        except Exception as e:
            print(f"Error: {e}\n")


if __name__ == "__main__":
    main()