# Indus - Personal AI Assistant

Advanced local AI assistant with memory, vision, system control, web automation, and real-time voice.

## Features

- **Memory**: SQLite hot memory + Vector DB (Qdrant/Chroma) + Knowledge Graph (NetworkX)
- **Voice**: Wake word detection, STT (Whisper), TTS (Edge/ElevenLabs), **Gemini Live real-time streaming**
- **Vision**: Screen analysis (NVIDIA Llama 3.2 Vision), Camera access, Face recognition, Object detection (YOLOv8)
- **System Control**: App launcher, Window management, Volume/Brightness, Theme toggle, Screenshots
- **Web Automation**: YouTube, WhatsApp Web (Playwright, Edge/Chrome)
- **Proactive Intelligence**: Routine learning, Context monitoring, Suggestion engine
- **Plugin System**: Dynamic plugin loading with custom skills

## Setup

```powershell
cd "D:\Ansh Kesharwani\Documents\indus-phase1\indus"
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
notepad .env
# Add your API keys
```

## Run Modes

```powershell
# Text mode (default)
python main.py

# Text mode with TTS output
python main.py --tts

# Voice mode (Wake word -> STT -> LLM -> TTS)
python main.py --voice

# Gemini Live real-time bidirectional voice streaming (NEW!)
python main.py --live-voice

# Use specific provider
python main.py --provider gemini
python main.py --provider nvidia
python main.py --provider mock
```

## Environment Variables (.env)

```env
# LLM Providers
PROVIDER=nvidia                    # gemini, nvidia, mock
NVIDIA_API_KEY=your_nvidia_key
GEMINI_API_KEY=your_gemini_key

# TTS
ELEVENLABS_API_KEY=your_elevenlabs_key
ELEVENLABS_VOICE_ID=your_voice_id

# Gemini Live Voice
GEMINI_LIVE_VOICE=Aoede            # Aoede, Puck, Charon, Kore, Fenrir

# Voice Wake Word (Picovoice)
PICOVOICE_ACCESS_KEY=your_picovoice_key
```

## Voice Modes Comparison

| Mode | Latency | Architecture | Use Case |
|------|---------|--------------|----------|
| `--voice` | ~2-3s | Wake Word → STT → LLM → TTS | Turn-based conversation |
| `--live-voice` | ~200-500ms | WebSocket streaming (Gemini Live) | Natural real-time conversation |

## Commands (Text/Voice)

```
Memory:     "what did I say about python?", "remember I prefer dark mode", "memory stats"
Screen:     "what's on my screen?", "read screen", "find terminal on screen"
Vision:     "start screen share vision", "start live screen vision"
Camera:     "who's in front of camera", "enroll my face as Ansh"
Proactive:  "start proactive assistant", "show suggestions", "analyze my routines"
System:     "open notepad", "set volume 50", "toggle theme", "take screenshot"
Web:        "play youtube rick astley", "send whatsapp to Ansh hello"
```

## Project Structure

```
core/
  chat_engine.py       # Main conversation loop
  llm_provider.py      # LLM abstraction (Gemini/NVIDIA/Mock)
  memory/              # SQLite + Vector DB + Knowledge Graph
  voice/
    tts.py             # TTS (ElevenLabs, Edge, pyttsx3, OpenAI)
    gemini_live.py     # Gemini Live real-time streaming (NEW)
    stt.py             # Whisper speech-to-text
    wake_word.py       # Picovoice/Simulated wake word
    audio_io.py        # PyAudio input/output
  vision/              # Screen, Camera, Face, Objects, Live
  system/              # Windows, Shell, Screen, Launcher
  skills/              # Memory, Vision, System, Web, Proactive, etc.
  proactive/           # Context, Routines, Suggestions
  plugins/             # Dynamic plugin loader
providers/
  gemini_provider.py   # Google Gemini
  nvidia_provider.py   # NVIDIA Nemotron/Llama
  mock_provider.py     # Testing without API keys
```

## Tech Stack

- **LLM**: NVIDIA Nemotron 3 Ultra / Gemini / Mock
- **Vision**: NVIDIA Llama 3.2 11B Vision Instruct
- **Voice**: Gemini Live API (real-time), Whisper STT, Edge/ElevenLabs TTS
- **Memory**: SQLite + Qdrant/Chroma + NetworkX Knowledge Graph
- **Automation**: Playwright, OpenCV, mss, pycaw
- **Plugins**: Dynamic Python import system

## Requirements

See `requirements.txt` for full list. Key packages:
- `google-genai` (Gemini Live)
- `edge-tts`, `openai`, `pvporcupine`
- `torch`, `torchvision`, `ultralytics`, `insightface`
- `qdrant-client`, `chromadb`, `networkx`
- `playwright`, `opencv-python`, `mss`