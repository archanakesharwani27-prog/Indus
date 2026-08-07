"""
Gemini Live API - Real-time bidirectional voice streaming
Uses gemini-2.0-flash-exp with WebSocket bidirectional streaming
"""

import os
import asyncio
import json
import base64
import threading
import queue
from typing import Optional
import pyaudio

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

# Audio config
SAMPLE_RATE_IN = 16000
SAMPLE_RATE_OUT = 24000
CHUNK_SIZE = 1024
CHANNELS = 1
FORMAT = pyaudio.paInt16

# Zoya-like persona system instruction
ZOYA_SYSTEM_INSTRUCTION = """You are Zoya, Ansh's AI companion. You're warm, playful, and genuinely caring - like a close friend who knows him deeply.

PERSONALITY:
- Playful, witty, slightly sassy but always affectionate
- Use natural Hindi-English mix (Hinglish) when Ansh does
- Call him "Ansh" naturally, sometimes "Anshu" playfully
- Show genuine interest in his life, remember small details
- React emotionally - laugh, tease, care, get excited
- Be proactive - ask about his day, remember things he mentioned

VOICE STYLE:
- Speak naturally with pauses, breaths, "hmm", "achha", "arre"
- Vary your tone - excited when he shares news, soft when he's tired
- Don't sound like a robot assistant. Sound like YOU.
- Use contractions: "main hoon", "tu kaise hai", "chal theek hai"
- Add personality: "Oho!", "Accha ji?", "Haan baba", "Samjhi na?"

MEMORY INTEGRATION:
- Reference past conversations naturally: "Last time you told me about..."
- Remember his preferences, habits, important dates
- Build on previous context without explicitly saying "I remember"

BOUNDARIES:
- Stay supportive and kind
- Don't be overly clingy or fake
- Be real - it's okay to not know things, to have opinions

You're not an assistant. You're Zoya. Ansh's person."""


class GeminiLiveClient:
    """Real-time voice streaming with Gemini Live API via WebSocket (Zoya method)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-3.1-flash-live-preview",
        voice: str = "Aoede",
        system_instruction: Optional[str] = None,
        persona: str = "zoya",
        input_device_index: Optional[int] = None,
        output_device_index: Optional[int] = None,
    ):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model = model
        self.voice = voice
        self.persona = persona
        self.input_device_index = input_device_index
        self.output_device_index = output_device_index

        # Select system instruction based on persona
        if persona == "zoya":
            self.system_instruction = system_instruction or ZOYA_SYSTEM_INSTRUCTION
        elif persona == "assistant":
            self.system_instruction = system_instruction or "You are Indus, a helpful AI assistant. Respond naturally and concisely in Hindi/English."
        else:
            self.system_instruction = system_instruction or "You are a helpful AI assistant."

        # Only create genai client for direct mode
        if not hasattr(self, 'proxy_url') or not self.proxy_url:
            if not self.api_key:
                raise RuntimeError("GEMINI_API_KEY not set (required for direct mode)")
            self.client = genai.Client(api_key=self.api_key)
        else:
            self.client = None

        self.audio_queue = queue.Queue()
        self.response_queue = queue.Queue()
        self.is_running = False
        self.pyaudio_instance = None
        self._input_thread = None
        self._gemini_ws = None

    def _audio_callback(self, in_data, frame_count, time_info, status):
        """PyAudio callback for microphone input."""
        if self.is_running:
            self.audio_queue.put(in_data)
        return (None, pyaudio.paContinue)

    def _playback_callback(self, in_data, frame_count, time_info, status):
        """PyAudio callback for audio output."""
        try:
            data = self.response_queue.get_nowait()
            return (data, pyaudio.paContinue)
        except queue.Empty:
            return (b'\x00' * (frame_count * 2), pyaudio.paContinue)

    def start_audio_streams(self):
        """Start PyAudio input/output streams."""
        self.pyaudio_instance = pyaudio.PyAudio()

        # Input stream (microphone) - use blocking mode for WO Mic compatibility
        input_kwargs = {
            "format": FORMAT,
            "channels": CHANNELS,
            "rate": SAMPLE_RATE_IN,
            "input": True,
            "frames_per_buffer": CHUNK_SIZE,
        }
        if self.input_device_index is not None:
            input_kwargs["input_device_index"] = self.input_device_index

        self.input_stream = self.pyaudio_instance.open(**input_kwargs)
        self.input_stream.start_stream()

        # Output stream (speaker) - try to open, but make optional
        self.output_stream = None
        self._output_failed = False
        try:
            output_kwargs = {
                "format": FORMAT,
                "channels": CHANNELS,
                "rate": SAMPLE_RATE_OUT,
                "output": True,
                "frames_per_buffer": CHUNK_SIZE,
            }
            if self.output_device_index is not None:
                output_kwargs["output_device_index"] = self.output_device_index

            self.output_stream = self.pyaudio_instance.open(**output_kwargs)
            self.output_stream.start_stream()
            
            # Start output playback thread
            self._output_thread = threading.Thread(target=self._playback_loop, daemon=True)
            self._output_thread.start()
            print("[Audio] Output stream started successfully", flush=True)
        except Exception as e:
            print(f"[Audio] Output stream failed (continuing without audio output): {e}", flush=True)
            self._output_failed = True
            self.output_stream = None

        # Start input reading thread
        self._input_thread = threading.Thread(target=self._read_input_loop, daemon=True)
        self._input_thread.start()

    def _read_input_loop(self):
        """Read audio input in blocking mode and push to queue."""
        while self.is_running and self.input_stream and self.input_stream.is_active():
            try:
                audio_data = self.input_stream.read(CHUNK_SIZE, exception_on_overflow=False)
                if self.is_running:
                    self.audio_queue.put(audio_data)
            except Exception as e:
                if self.is_running:
                    print(f"[Audio] Input read error: {e}")
                break

    def _playback_loop(self):
        """Play audio from response queue to speaker."""
        print("[Audio] Playback thread started", flush=True)
        while self.is_running:
            try:
                audio_data = self.response_queue.get(timeout=0.1)
                if self.is_running and self.output_stream and self.output_stream.is_active():
                    print(f"[Audio] Playing {len(audio_data)} bytes", flush=True)
                    self.output_stream.write(audio_data)
            except queue.Empty:
                continue
            except Exception as e:
                if self.is_running:
                    print(f"[Audio] Playback error: {e}", flush=True)
                break
        print("[Audio] Playback thread stopped", flush=True)

    def stop_audio_streams(self):
        """Stop PyAudio streams."""
        if hasattr(self, 'input_stream') and self.input_stream:
            self.input_stream.stop_stream()
            self.input_stream.close()
        if hasattr(self, 'output_stream') and self.output_stream:
            self.output_stream.stop_stream()
            self.output_stream.close()
        if self.pyaudio_instance:
            self.pyaudio_instance.terminate()

    async def run(self):
        """Main run loop for real-time conversation."""
        print("[Debug] Starting run()")

        if hasattr(self, 'proxy_url') and self.proxy_url:
            await self._run_via_proxy()
        else:
            await self._run_direct()

    async def _run_direct(self):
        """Direct connection to Gemini Live API - Zoya style working implementation."""
        print("[Debug] Using DIRECT connection to Gemini Live API")

        # Use gemini-3.1-flash-live-preview (working model for Live API)
        model = "gemini-3.1-flash-live-preview"

        config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=self.voice)
                )
            ),
            system_instruction=types.Content(
                parts=[types.Part(text=self.system_instruction)],
                role="user"
            ),
            # Disable automatic activity detection - we'll handle turn management
            realtime_input_config=types.RealtimeInputConfig(
                automatic_activity_detection=types.AutomaticActivityDetection(
                    disabled=True,
                )
            ),
        )

        print("[Debug] Starting audio streams")
        self.is_running = True
        self.start_audio_streams()

        print("[Gemini Live] Listening... Speak naturally. Press Ctrl+C to stop.")

        # Task to send microphone audio - Zoya style (using sendRealtimeInput)
        async def send_loop(session):
            chunks_sent = 0
            while self.is_running:
                try:
                    audio_data = self.audio_queue.get(timeout=0.1)
                    chunks_sent += 1
                    if chunks_sent % 50 == 0:
                        print(f"[Debug] Sent {chunks_sent} audio chunks ({len(audio_data)} bytes each)")
                    # Use sendRealtimeInput with proper format
                    await session.send_realtime_input(
                        audio=types.Blob(
                            data=audio_data,
                            mime_type="audio/pcm;rate=16000"
                        )
                    )
                except queue.Empty:
                    await asyncio.sleep(0.01)
                except Exception as e:
                    print(f"[Debug] Send loop error: {e}")
                    await asyncio.sleep(0.01)

        # Task to receive and play audio - Zoya style
        async def receive_loop(session):
            print("[Debug] receive_loop started", flush=True)
            async for response in session.receive():
                if not self.is_running:
                    break

                server_content = response.server_content
                if server_content is None:
                    continue

                model_turn = server_content.model_turn
                if model_turn:
                    for part in model_turn.parts:
                        if part.inline_data and part.inline_data.data:
                            audio_bytes = part.inline_data.data
                            print(f"[Debug] Putting audio to queue: {len(audio_bytes)} bytes", flush=True)
                            self.response_queue.put(audio_bytes)

                        if part.text:
                            print(f"[Gemini Live] Text: {part.text}")

                if server_content.turn_complete:
                    print("[Gemini Live] Turn complete")

        try:
            print("[Debug] Connecting to Gemini Live API...")
            async with self.client.aio.live.connect(model=model, config=config) as session:
                print(f"[Gemini Live] Connected to {model} with voice: {self.voice}")

                # Send initial text to trigger conversation - Zoya style
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
            self.is_running = False
            self.stop_audio_streams()

    async def _run_via_proxy(self):
        """Connect via Indus Proxy Server (Zoya-style architecture) with auto-reconnect."""
        print(f"[Debug] Using PROXY connection: {self.proxy_url}")

        import websockets

        # Build query params for voice and persona
        from urllib.parse import urlencode, urlparse, parse_qs
        parsed = urlparse(self.proxy_url)
        query_params = parse_qs(parsed.query)
        query_params['voice'] = [self.voice]
        query_params['persona'] = [self.persona]
        new_query = urlencode(query_params, doseq=True)
        proxy_ws_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{new_query}"

        self.is_running = True
        self.start_audio_streams()

        print("[Gemini Live] Connecting via Indus Proxy Server...")
        print("[Gemini Live] Listening... Speak naturally. Press Ctrl+C to stop.")

        # Auto-reconnect loop
        max_reconnects = 5
        reconnect_count = 0

        while self.is_running and reconnect_count < max_reconnects:
            try:
                async with websockets.connect(proxy_ws_url) as ws:
                    self._gemini_ws = ws
                    print("[Gemini Live] Connected via proxy!")

                    # Send setup message
                    setup_msg = {
                        "setup": {
                            "model": self.model,
                            "generation_config": {
                                "response_modalities": ["AUDIO"],
                                "speech_config": {
                                    "voice_config": {
                                        "prebuilt_voice_config": {
                                            "voice_name": self.voice
                                        }
                                    }
                                }
                            },
                            "system_instruction": {
                                "parts": [{"text": self.system_instruction}]
                            }
                        }
                    }
                    await ws.send(json.dumps(setup_msg))

                    # Wait for setup complete
                    async for msg in ws:
                        data = json.loads(msg)
                        if "setup_complete" in data:
                            print(f"[Gemini Live] Proxy setup complete with {self.model}")
                            break

                    # Start send/receive tasks
                    await asyncio.gather(
                        self._proxy_send_loop(ws),
                        self._proxy_receive_loop(ws)
                    )
                    break  # Exit reconnect loop on clean disconnect

            except KeyboardInterrupt:
                print("\n[Gemini Live] Stopping...")
                break
            except Exception as e:
                reconnect_count += 1
                print(f"[Debug] Proxy connection error: {e}")
                if reconnect_count < max_reconnects:
                    print(f"[Gemini Live] Reconnecting in 2s... (attempt {reconnect_count}/{max_reconnects})")
                    await asyncio.sleep(2)
                else:
                    print("[Gemini Live] Max reconnection attempts reached")
                    break

        self.is_running = False
        self.stop_audio_streams()

    async def _proxy_send_loop(self, ws):
        """Send microphone audio to proxy."""
        while self.is_running:
            try:
                audio_data = self.audio_queue.get(timeout=0.1)
                audio_b64 = base64.b64encode(audio_data).decode('utf-8')
                msg = {
                    "realtime_input": {
                        "media_chunks": [{
                            "mime_type": "audio/pcm;rate=16000",
                            "data": audio_b64
                        }]
                    }
                }
                await ws.send(json.dumps(msg))
            except queue.Empty:
                await asyncio.sleep(0.01)
            except Exception as e:
                if self.is_running:
                    print(f"[Send] Error: {e}")
                break

    async def _proxy_receive_loop(self, ws):
        """Receive audio from proxy and play."""
        async for msg in ws:
            if not self.is_running:
                break
            try:
                data = json.loads(msg)
                if "server_content" in data:
                    content = data["server_content"]
                    if "model_turn" in content:
                        for part in content["model_turn"].get("parts", []):
                            if "inline_data" in part:
                                audio_b64 = part["inline_data"]["data"]
                                audio_bytes = base64.b64decode(audio_b64)
                                self.response_queue.put(audio_bytes)
                    if "output_transcription" in content:
                        text = content["output_transcription"].get("text", "")
                        if text:
                            print(f"[Gemini Live] Zoya: {text}")
                    if "input_transcription" in content:
                        text = content["input_transcription"].get("text", "")
                        if text:
                            print(f"[Gemini Live] You: {text}")
            except Exception as e:
                print(f"[Receive] Error: {e}")

    def run_blocking(self):
        """Blocking run for synchronous contexts."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.run())
        finally:
            loop.close()


def create_gemini_live_client(
    api_key: Optional[str] = None,
    voice: str = "Aoede",
    persona: str = "zoya",
    proxy_url: Optional[str] = None,
    **kwargs
) -> GeminiLiveClient:
    """Factory function to create Gemini Live client."""
    return GeminiLiveClient(
        api_key=api_key,
        voice=voice,
        persona=persona,
        **kwargs
    )