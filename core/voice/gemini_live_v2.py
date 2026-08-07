"""
Gemini Live API v2 - WebSocket-based real-time bidirectional voice streaming (Zoya method)
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
import websockets


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


# System tools for PC control (function calling)
SYSTEM_TOOLS = [
    {
        "name": "control_pc_app",
        "description": "Launch or control PC desktop applications",
        "parameters": {
            "type": "object",
            "properties": {
                "app_name": {"type": "string", "description": "Application name to launch (e.g., notepad, calculator, chrome, vscode)"},
                "action": {"type": "string", "enum": ["open", "close", "focus"], "description": "Action to perform", "default": "open"}
            },
            "required": ["app_name"]
        }
    },
    {
        "name": "control_volume",
        "description": "Control system audio volume",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["up", "down", "set", "mute", "unmute", "get"]},
                "level": {"type": "integer", "description": "Volume level 0-100 (for set action)"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "web_search",
        "description": "Search the web using Google",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "youtube_play",
        "description": "Play video on YouTube",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Video search query"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "screenshot",
        "description": "Take a screenshot of the screen",
        "parameters": {
            "type": "object",
            "properties": {
                "region": {"type": "string", "enum": ["full", "window"], "default": "full"}
            }
        }
    },
    {
        "name": "list_windows",
        "description": "List all open windows",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    }
]


class GeminiLiveV2:
    """Real-time voice streaming with Gemini Live API via WebSocket (Zoya method)."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-2.0-flash-exp",
        voice: str = "Aoede",
        system_instruction: Optional[str] = None,
        persona: str = "zoya",
        input_device_index: Optional[int] = None,
    ):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY not set")
        
        self.model = model
        self.voice = voice
        self.persona = persona
        self.input_device_index = input_device_index
        
        # Select system instruction based on persona
        if persona == "zoya":
            self.system_instruction = system_instruction or ZOYA_SYSTEM_INSTRUCTION
        elif persona == "assistant":
            self.system_instruction = system_instruction or "You are Indus, a helpful AI assistant. Respond naturally and concisely in Hindi/English."
        else:
            self.system_instruction = system_instruction or "You are a helpful AI assistant."
        
        self.ws_url = f"wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContent?key={self.api_key}"
        
        self.audio_queue = queue.Queue()
        self.response_queue = queue.Queue()
        self.is_running = False
        self.pyaudio_instance = None
        self.ws = None
        
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
        
        # Output stream (speaker) - callback for playback
        self.output_stream = self.pyaudio_instance.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=SAMPLE_RATE_OUT,
            output=True,
            frames_per_buffer=CHUNK_SIZE,
            stream_callback=self._playback_callback,
        )
        
        self.input_stream.start_stream()
        self.output_stream.start_stream()
        
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
    
    def _playback_callback(self, in_data, frame_count, time_info, status):
        """PyAudio callback for audio output."""
        try:
            data = self.response_queue.get_nowait()
            return (data, pyaudio.paContinue)
        except queue.Empty:
            return (b'\x00' * (frame_count * 2), pyaudio.paContinue)
    
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
        """Main run loop for real-time conversation via WebSocket."""
        print("[Gemini Live v2] Starting WebSocket connection...")
        
        self.is_running = True
        self.start_audio_streams()
        
        print("[Gemini Live v2] Listening... Speak naturally. Press Ctrl+C to stop.")
        
        try:
            async with websockets.connect(self.ws_url) as ws:
                self.ws = ws
                print("[Gemini Live v2] WebSocket connected")
                
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
                        },
                        "tools": [{"function_declarations": SYSTEM_TOOLS}]
                    }
                }
                await ws.send(json.dumps(setup_msg))
                print("[Gemini Live v2] Setup sent")
                
                # Wait for setup complete
                async for msg in ws:
                    data = json.loads(msg)
                    if "setup_complete" in data:
                        print(f"[Gemini Live v2] Connected to {self.model} with voice: {self.voice}")
                        break
                
                # Start send/receive tasks
                await asyncio.gather(
                    self._send_loop(ws),
                    self._receive_loop(ws)
                )
                
        except KeyboardInterrupt:
            print("\n[Gemini Live v2] Stopping...")
        except Exception as e:
            print(f"[Gemini Live v2] Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.is_running = False
            self.stop_audio_streams()
    
    async def _send_loop(self, ws):
        """Send microphone audio to Gemini."""
        chunks_sent = 0
        while self.is_running:
            try:
                audio_data = self.audio_queue.get(timeout=0.1)
                chunks_sent += 1
                
                # Convert to base64
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
    
    async def _receive_loop(self, ws):
        """Receive audio and tool calls from Gemini."""
        async for msg in ws:
            if not self.is_running:
                break
            
            try:
                data = json.loads(msg)
                
                # Handle server content (audio + text)
                if "server_content" in data:
                    content = data["server_content"]
                    
                    # Handle model turn (audio output)
                    if "model_turn" in content:
                        for part in content["model_turn"].get("parts", []):
                            if "inline_data" in part:
                                audio_b64 = part["inline_data"]["data"]
                                audio_bytes = base64.b64decode(audio_b64)
                                self.response_queue.put(audio_bytes)
                    
                    # Handle text transcription
                    if "output_transcription" in content:
                        text = content["output_transcription"].get("text", "")
                        if text:
                            print(f"[Gemini Live v2] Zoya: {text}")
                    
                    if "input_transcription" in content:
                        text = content["input_transcription"].get("text", "")
                        if text:
                            print(f"[Gemini Live v2] You: {text}")
                
                # Handle tool calls
                if "tool_call" in data:
                    tool_call = data["tool_call"]
                    print(f"[Gemini Live v2] Tool call: {tool_call['name']}")
                    result = await self._execute_tool(tool_call)
                    
                    # Send tool response back
                    response_msg = {
                        "tool_response": {
                            "function_responses": [{
                                "name": tool_call["name"],
                                "id": tool_call.get("id", ""),
                                "response": {"result": result}
                            }]
                        }
                    }
                    await ws.send(json.dumps(response_msg))
                    
            except Exception as e:
                print(f"[Receive] Error: {e}")
    
    async def _execute_tool(self, tool_call):
        """Execute a tool call and return result."""
        name = tool_call["name"]
        args = tool_call.get("args", {})
        
        try:
            if name == "control_pc_app":
                return await self._control_pc_app(args)
            elif name == "control_volume":
                return await self._control_volume(args)
            elif name == "web_search":
                return await self._web_search(args)
            elif name == "youtube_play":
                return await self._youtube_play(args)
            elif name == "screenshot":
                return await self._screenshot(args)
            elif name == "list_windows":
                return await self._list_windows(args)
            else:
                return {"error": f"Unknown tool: {name}"}
        except Exception as e:
            return {"error": str(e)}
    
    async def _control_pc_app(self, args):
        """Launch/close/focus PC application."""
        import subprocess
        app_name = args.get("app_name", "").lower()
        action = args.get("action", "open")
        
        app_commands = {
            "notepad": "notepad.exe",
            "calculator": "calc.exe",
            "chrome": "chrome.exe",
            "vscode": "code.exe",
            "cmd": "cmd.exe",
            "powershell": "powershell.exe",
            "explorer": "explorer.exe",
        }
        
        if action == "open":
            cmd = app_commands.get(app_name, app_name)
            subprocess.Popen(cmd, shell=True)
            return {"status": "opened", "app": app_name}
        elif action == "close":
            subprocess.run(f"taskkill /f /im {app_commands.get(app_name, app_name)}", shell=True)
            return {"status": "closed", "app": app_name}
        return {"status": "unknown_action"}
    
    async def _control_volume(self, args):
        """Control system volume."""
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        
        action = args.get("action", "get")
        level = args.get("level", 50)
        
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        
        if action == "up":
            current = volume.GetMasterVolumeLevelScalar()
            volume.SetMasterVolumeLevelScalar(min(1.0, current + 0.1), None)
        elif action == "down":
            current = volume.GetMasterVolumeLevelScalar()
            volume.SetMasterVolumeLevelScalar(max(0.0, current - 0.1), None)
        elif action == "set":
            volume.SetMasterVolumeLevelScalar(level / 100.0, None)
        elif action == "mute":
            volume.SetMute(1, None)
        elif action == "unmute":
            volume.SetMute(0, None)
        
        current = volume.GetMasterVolumeLevelScalar()
        return {"status": "ok", "volume": int(current * 100)}
    
    async def _web_search(self, args):
        """Search the web."""
        import webbrowser
        query = args.get("query", "")
        url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        webbrowser.open(url)
        return {"status": "opened", "query": query}
    
    async def _youtube_play(self, args):
        """Play YouTube video."""
        import webbrowser
        query = args.get("query", "")
        url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
        webbrowser.open(url)
        return {"status": "opened", "query": query}
    
    async def _screenshot(self, args):
        """Take screenshot."""
        import pyautogui
        import tempfile
        region = args.get("region", "full")
        tmp_path = tempfile.mktemp(suffix=".png")
        pyautogui.screenshot(tmp_path)
        return {"status": "saved", "path": tmp_path}
    
    async def _list_windows(self, args):
        """List open windows."""
        import pygetwindow as gw
        windows = gw.getAllTitles()
        return {"windows": [w for w in windows if w.strip()]}
    
    def run_blocking(self):
        """Blocking run for synchronous contexts."""
        asyncio.run(self.run())


def create_gemini_live_v2(
    api_key: Optional[str] = None,
    voice: str = "Aoede",
    persona: str = "zoya",
    **kwargs
) -> GeminiLiveV2:
    """Factory function to create Gemini Live v2 client."""
    return GeminiLiveV2(api_key=api_key, voice=voice, persona=persona, **kwargs)