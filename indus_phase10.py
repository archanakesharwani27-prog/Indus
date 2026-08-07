"""
Indus Phase 10 - Continuous Voice Assistant with Real APIs
Real-time voice command execution with multi-agent collaboration.
"""

import os
import sys
import signal
import threading
import time
import json
import queue
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# Core imports
from core.memory import Memory
from core.chat_engine import ChatEngine
from core.llm_provider import LLMProvider
from providers.nvidia_provider import NVIDIAProvider
from providers.gemini_provider import GeminiProvider
from core.voice.gemini_live import GeminiLiveClient, create_gemini_live_client
from core.voice.groq_tts import TTSClient, create_tts_client
from core.multiagent import create_orchestrator, AgentRole
from core.voice.audio_io import AudioConfig, AudioStream


class IndusVoiceAssistant:
    """Continuous voice assistant with real API integration."""
    
    def __init__(self):
        self.running = False
        self.listening = False
        
        # Initialize providers
        self.llm_provider = self._init_llm_provider()
        self.tts = self._init_tts()
        self.gemini_live = self._init_gemini_live()
        
        # Initialize memory and chat engine
        self.memory = Memory(db_path="indus.db")
        self.engine = ChatEngine(
            provider=self.llm_provider,
            memory=self.memory,
            use_intents=True,
            enable_semantic_memory=True,
            persona="zoya",
        )
        
        # Initialize multi-agent orchestrator
        self.orchestrator = create_orchestrator(llm_provider=self.llm_provider)
        
        # Voice state
        self.audio_config = AudioConfig()
        self.audio_stream = AudioStream(self.audio_config)
        self.whisper = None  # Will init when needed
        
        # Track if we have an active transcription
        self._last_transcription = ""
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        print("[Indus] Voice assistant initialized with real APIs")
    
    def _init_llm_provider(self) -> LLMProvider:
        """Initialize LLM provider from env."""
        provider_name = os.getenv("PROVIDER", "nvidia").lower()
        
        if provider_name == "nvidia":
            return NVIDIAProvider(persona="zoya")
        elif provider_name == "gemini":
            return GeminiProvider(persona="zoya")
        else:
            # Fallback to NVIDIA
            return NVIDIAProvider(persona="zoya")
    
    def _init_tts(self) -> Optional[TTSClient]:
        """Initialize TTS client."""
        try:
            # Try Groq TTS first (requires GROQ_API_KEY)
            groq_key = os.getenv("GROQ_API_KEY")
            if groq_key:
                return create_tts_client(backend="groq", voice="Arista")
            # Fallback to Edge TTS
            return create_tts_client(backend="edge", voice="en-US-AriaNeural")
        except Exception as e:
            print(f"[TTS] Warning: Could not initialize TTS: {e}")
            return None
    
    def _init_gemini_live(self) -> Optional[GeminiLiveClient]:
        """Initialize Gemini Live for real-time voice."""
        try:
            gemini_key = os.getenv("GEMINI_API_KEY")
            if gemini_key:
                voice = os.getenv("GEMINI_LIVE_VOICE", "Aoede")
                persona = os.getenv("GEMINI_LIVE_PERSONA", "zoya")
                proxy_url = os.getenv("PROXY_URL")
                
                if proxy_url:
                    print(f"[Gemini Live] Using proxy: {proxy_url}")
                return create_gemini_live_client(
                    api_key=gemini_key,
                    voice=voice,
                    persona=persona,
                    proxy_url=proxy_url,
                )
        except Exception as e:
            print(f"[Gemini Live] Warning: Could not initialize: {e}")
        return None
    
    def _signal_handler(self, sig, frame):
        print("\n[Indus] Shutting down...")
        self.stop()
        sys.exit(0)
    
    def speak(self, text: str):
        """Speak text using TTS."""
        if self.tts:
            print(f"[Indus] Speaking: {text}")
            self.tts.speak(text)
        else:
            print(f"[Indus] (No TTS) {text}")
    
    def _execute_with_voice_confirmation(self, user_input: str) -> str:
        """Execute user command and provide voice confirmation."""
        try:
            # Check if it's a multi-agent task
            if any(keyword in user_input.lower() for keyword in [
                "plan", "research", "workflow", "delegate", "team", "multiagent"
            ]):
                # Use multi-agent orchestrator
                result = self.orchestrator.run_workflow(
                    "research_plan_execute_verify",
                    user_input
                )
                if "error" not in result:
                    response = f"Task completed. {result.get('results', {}).get('verify', {}).get('message', 'Done')}"
                else:
                    response = f"Task failed: {result.get('error', 'Unknown error')}"
            else:
                # Use regular chat engine for simple commands
                response = self.engine.respond(user_input)
            
            # Speak the response
            self.speak(response)
            return response
            
        except Exception as e:
            error_msg = f"Error executing command: {str(e)}"
            print(f"[Indus] {error_msg}")
            self.speak(f"Sorry, I encountered an error: {str(e)}")
            return error_msg
    
    def _handle_transcription(self, text: str):
        """Handle transcription from Gemini Live."""
        if not text or not text.strip():
            return
        
        text = text.strip()
        print(f"[Indus] Transcription received: {text}")
        
        # Skip duplicate/short transcriptions
        if text == self._last_transcription or len(text) < 3:
            return
        self._last_transcription = text
        
        # Check for exit commands
        if text.lower() in ("exit", "quit", "stop", "bye", "goodbye"):
            self.speak("Goodbye!")
            self.running = False
            return
        
        # Execute command
        self._execute_with_voice_confirmation(text)
    
    def run_continuous_voice_mode(self):
        """Run continuous voice command loop using Gemini Live."""
        if not self.gemini_live:
            print("[Indus] Gemini Live not available, falling back to wake word mode")
            self.run_wake_word_mode()
            return
        
        print("[Indus] Starting continuous voice mode with Gemini Live...")
        print("[Indus] Speak naturally. Say 'exit' or 'quit' to stop.")
        self.speak("Hello! I'm ready. How can I help you?")
        
        self.running = True
        
        # Patch receive_loop to handle transcriptions
        original_run = self.gemini_live.run
        
        async def patched_run():
            print("[Debug] Starting run()")
            self.running = True
            
            if hasattr(self.gemini_live, 'proxy_url') and self.gemini_live.proxy_url:
                await self.gemini_live._run_via_proxy()
            else:
                await self._patched_run_direct()
        
        self.gemini_live.run = patched_run
        
        try:
            self.gemini_live.run_blocking()
        except KeyboardInterrupt:
            print("\n[Indus] Stopping...")
        finally:
            self.running = False
            self.speak("Goodbye!")
    
    async def _patched_run_direct(self):
        """Patched version that handles transcriptions."""
        from google import genai
        from google.genai import types
        import queue
        import asyncio
        
        print("[Debug] Using DIRECT connection to Gemini Live API")
        model = "gemini-3.1-flash-live-preview"
        
        config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=self.gemini_live.voice)
                )
            ),
            system_instruction=types.Content(
                parts=[types.Part(text=self.gemini_live.system_instruction)],
                role="user"
            ),
            realtime_input_config=types.RealtimeInputConfig(
                automatic_activity_detection=types.AutomaticActivityDetection(
                    disabled=False,
                )
            ),
            # Enable transcriptions
            input_audio_transcription=types.AudioTranscriptionConfig(
                language_codes=["en-US", "hi-IN"],
            ),
            output_audio_transcription=types.AudioTranscriptionConfig(
                language_codes=["en-US", "hi-IN"],
            ),
        )
        
        print("[Debug] Starting audio streams")
        self.gemini_live.is_running = True
        self.gemini_live.start_audio_streams()
        
        print("[Gemini Live] Listening... Speak naturally. Say 'exit' or 'quit' to stop.")
        
        # Task to send microphone audio
        async def send_loop(session):
            chunks_sent = 0
            while self.gemini_live.is_running:
                try:
                    audio_data = self.gemini_live.audio_queue.get(timeout=0.1)
                    chunks_sent += 1
                    if chunks_sent % 50 == 0:
                        print(f"[Debug] Sent {chunks_sent} audio chunks", flush=True)
                    await session.send_realtime_input(
                        audio=types.Blob(
                            data=audio_data,
                            mime_type="audio/pcm;rate=16000"
                        )
                    )
                except queue.Empty:
                    await asyncio.sleep(0.01)
                except Exception as e:
                    print(f"[Debug] Send loop error: {e}", flush=True)
                    await asyncio.sleep(0.01)
        
        # Task to receive and handle transcriptions
        async def receive_loop(session):
            print("[Debug] receive_loop started", flush=True)
            async for response in session.receive():
                if not self.gemini_live.is_running:
                    break
                
                server_content = response.server_content
                if server_content is None:
                    continue
                
                model_turn = server_content.model_turn
                if model_turn:
                    for part in model_turn.parts:
                        if part.inline_data and part.inline_data.data:
                            audio_bytes = part.inline_data.data
                            self.gemini_live.response_queue.put(audio_bytes)
                        
                        if part.text:
                            # Handle transcription from Zoya
                            print(f"[Gemini Live] Zoya: {part.text}")
                            # We could speak Zoya's response here if needed
                
# Handle user transcription
                if hasattr(server_content, 'input_audio_transcription') and server_content.input_audio_transcription:
                    text = server_content.input_audio_transcription.text if hasattr(server_content.input_audio_transcription, 'text') else str(server_content.input_audio_transcription)
                    if text:
                        print(f"[Gemini Live] You: {text}")
                        self._handle_transcription(text)
                
                # Handle interim transcription (partial results while speaking)
                if hasattr(server_content, 'interim_input_audio_transcription') and server_content.interim_input_audio_transcription:
                    text = server_content.interim_input_audio_transcription.text if hasattr(server_content.interim_input_audio_transcription, 'text') else str(server_content.interim_input_audio_transcription)
                    if text:
                        print(f"[Gemini Live] You (interim): {text}")
                
                # Also check for input_transcription (older field name)
                if hasattr(server_content, 'input_transcription') and server_content.input_transcription:
                    text = server_content.input_transcription.get("text", "") if isinstance(server_content.input_transcription, dict) else str(server_content.input_transcription)
                    if text:
                        print(f"[Gemini Live] You: {text}")
                        self._handle_transcription(text)
                
                if getattr(server_content, 'turn_complete', False):
                    print("[Gemini Live] Turn complete")
        
        try:
            print("[Debug] Connecting to Gemini Live API...")
            async with self.gemini_live.client.aio.live.connect(model=model, config=config) as session:
                print(f"[Gemini Live] Connected to {model} with voice: {self.gemini_live.voice}")
                
                # Send initial text to trigger conversation
                await session.send_client_content(
                    turns=[types.Content(parts=[types.Part(text="Say hello and introduce yourself as Zoya.")], role="user")],
                    turn_complete=True
                )
                
                await asyncio.gather(send_loop(session), receive_loop(session))
        except KeyboardInterrupt:
            print("\n[Gemini Live] Stopping...")
        except Exception as e:
            print(f"[Debug] Error in run(): {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.gemini_live.is_running = False
            self.gemini_live.stop_audio_streams()
    
    def run_wake_word_mode(self):
        """Run wake word + STT + TTS mode (fallback)."""
        print("[Indus] Starting wake word mode...")
        print("[Indus] Say 'Hey Indus' or 'Jarvis' to activate")
        self.speak("Wake word mode active. Say Hey Indus to start.")
        
        # Initialize STT
        try:
            from core.voice.stt import WhisperClient
            self.whisper = WhisperClient()
        except Exception as e:
            print(f"[STT] Warning: {e}")
        
        # Initialize wake word detector
        try:
            from core.voice.wake_word import WakeWordDetector, SimpleWakeWordDetector
            has_picovoice = bool(os.getenv("PICOVOICE_ACCESS_KEY"))
            if has_picovoice:
                self.wake_detector = WakeWordDetector(
                    keywords=["jarvis", "hey google"],
                    on_detected=self._on_wake_word,
                )
            else:
                self.wake_detector = SimpleWakeWordDetector(
                    keywords=["hey indus", "jarvis", "indus"],
                    on_detected=self._on_wake_word,
                )
        except Exception as e:
            print(f"[Wake Word] Warning: {e}")
            self.wake_detector = None
        
        if self.wake_detector:
            self.wake_detector.start()
            self.running = True
            
            try:
                while self.running:
                    time.sleep(0.5)
            except KeyboardInterrupt:
                print("\n[Indus] Stopping...")
            finally:
                if self.wake_detector:
                    self.wake_detector.stop()
                self.running = False
                self.speak("Goodbye!")
        else:
            print("[Indus] No wake word detector available")
    
    def _on_wake_word(self, keyword: str):
        """Callback when wake word detected."""
        print(f"\n[Wake Word] Detected: {keyword}")
        self.speak("Yes? I'm listening.")
        self._listen_and_execute()
    
    def _listen_and_execute(self):
        """Record audio, transcribe, execute, respond."""
        if not self.whisper:
            print("[STT] Whisper not available")
            return
        
        print("[Indus] Recording...")
        try:
            audio_data = self.audio_stream.record_until_silence()
            if not audio_data:
                print("[Indus] No audio recorded")
                return
            
            print("[Indus] Transcribing...")
            text = self.whisper.transcribe(audio_data)
            print(f"[Indus] You said: {text}")
            
            if not text:
                self.speak("I didn't catch that. Please try again.")
                return
            
            if text.lower() in ("exit", "quit", "stop", "bye"):
                self.speak("Goodbye!")
                self.running = False
                return
            
            # Execute command
            self._execute_with_voice_confirmation(text)
            
        except Exception as e:
            print(f"[Indus] Error: {e}")
            self.speak("Sorry, I had an error processing that.")
    
    def stop(self):
        """Stop the assistant."""
        self.running = False
        if hasattr(self, 'engine'):
            self.engine.shutdown()
        print("[Indus] Stopped")


def main():
    """Main entry point for Phase 10 continuous voice assistant."""
    print("=" * 60)
    print("INDUS PHASE 10 - Continuous Voice Assistant")
    print("Real API Integration: NVIDIA/Gemini LLM + Gemini Live Voice")
    print("Multi-Agent Collaboration + Vision + TTS")
    print("=" * 60)
    
    # Check API keys
    nvidia_key = os.getenv("NVIDIA_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")
    
    if nvidia_key:
        print(f"[Config] NVIDIA API: OK ({nvidia_key[:10]}...)")
    else:
        print("[Config] NVIDIA API: NOT SET")
    
    if gemini_key:
        print(f"[Config] Gemini API: OK ({gemini_key[:10]}...)")
    else:
        print("[Config] Gemini API: NOT SET")
    
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        print("[Config] Groq TTS: OK")
    else:
        print("[Config] Groq TTS: NOT SET (using Edge TTS fallback)")
    
    print()
    
    # Create and run assistant
    assistant = IndusVoiceAssistant()
    
    # Determine mode
    if len(sys.argv) > 1 and sys.argv[1] == "--wake-word":
        assistant.run_wake_word_mode()
    else:
        assistant.run_continuous_voice_mode()


if __name__ == "__main__":
    main()