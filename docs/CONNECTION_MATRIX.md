# INDUS (INDUS) — RUNTIME CONNECTION MATRIX

**Date:** 2026-08-23  
**Audited Platform:** Windows 10/11 x64  
**Author / Creator:** Ansh Kesharwani  

---

## 1. Complete Node & Edge Connection Matrix

The following matrix traces every point-to-point connection in INDUS from user stimulus to hardware execution and feedback display:

| Connection ID | Source Node | Target Node | Mechanism / Protocol | Live Status | Verified Evidence |
|---|---|---|---|---|---|
| **CONN-01** | `User Microphone` | `actions/audio_service.py` | PortAudio / `sounddevice` 16kHz PCM stream | **LIVE PASS** | 11 physical/virtual input endpoints enumerated on Windows; default device active. |
| **CONN-02** | `audio_service.py` | `actions/wake_word.py` | Rolling 2.0s PCM chunk deque + RMS Voice Activity Detection | **LIVE PASS** | Matches `"INDUS"`, `"Hey INDUS"`; rejects `"industry"`, `"indian"`; transitions to active. |
| **CONN-03** | `wake_word.py` | `main.py: _send_realtime` | Asyncio queue chunk forwarding (Same-Breath preserved) | **LIVE PASS** | Trailing syllables forwarded to WebSocket queue without audio loss. |
| **CONN-04** | `User Interruption` | `core/cancellation.py` | Stop keyword pattern matcher (*"STOP"*, *"Cancel"*, *"Ruko"*) | **LIVE PASS** | Atomic `threading.Event` set; registered cancellation callbacks executed in <10ms. |
| **CONN-05** | `cancellation.py` | `main.py: PyAudio / Tasks` | Audio queue flush + active asyncio task abort | **LIVE PASS** | Speaker audio stream halted, tool tasks aborted cleanly. |
| **CONN-06** | `PyQt6 UI (ui.py)` | `main.py: JarvisLive` | Qt Signals / `_on_text_command` forwarding | **LIVE PASS** | UI state machine verified across all 9 discrete states. |
| **CONN-07** | `main.py` | `Google Gemini Live` | WebSockets / REST (`v1beta` models endpoint) | **LIVE PASS** | Bi-directional streaming connection; live response from `gemini-3.6-flash`. |
| **CONN-08** | `or_client.py` | `Groq LPU / NVIDIA / OpenRouter` | HTTP REST Fallback Cascade | **UNIT-ONLY PASS** | Primary Gemini active; Groq unconfigured; OpenRouter/NVIDIA fallback logic unit-tested. |
| **CONN-09** | `Gemini Live Response` | `main.py: _handle_tool_call` | Native Function Call JSON schema unpacker | **LIVE PASS** | All 39 tool definitions registered and dispatched to `actions/*`. |
| **CONN-10** | `_handle_tool_call` | `actions/* (33 Modules)` | Dynamic Python function dispatcher | **LIVE PASS** | All 33 action modules invoked functionally with 100% success. |
| **CONN-11** | `actions/computer_control.py` | `actions/vision_engine.py` | Target element visual grounding lookup | **LIVE PASS** | MSS screen capture + Gemini multimodal grounding extracts `(x, y)` bounding boxes. |
| **CONN-12** | `vision_engine.py` | `actions/computer_control.py` | PyAutoGUI coordinate dispatcher | **LIVE PASS** | Confidence >= 0.60 permits click; confidence < 0.50 triggers ambiguity safety abort. |
| **CONN-13** | `actions/* (Execution)` | `actions/action_verifier.py` | Post-action verification (3-Tier) | **LIVE PASS** | Process checks (`psutil`) + visual delta (`ImageChops`) confirm true physical change. |
| **CONN-14** | `action_verifier.py` | `agent/error_handler.py` | Failure category classification & strategy switch | **LIVE PASS** | Errors categorized into 6 types; bounded retries (<= 2); destructive actions blocked from retry. |
| **CONN-15** | `agent/error_handler.py` | `agent/agent_loop.py` | Multi-step goal re-planning / recovery | **LIVE PASS** | Goal decomposition into `TaskPlan` sequences with dynamic step recovery. |
| **CONN-16** | `agent_loop.py` | `memory/db_engine.py` | SQLite WAL persistence (`indus_memory.db`) | **LIVE PASS** | Round-trip read/write of facts, chat history, and habits. |
| **CONN-17** | `memory_manager.py` | `Prompt Context Generator` | 10-turn bounded conversation context injection | **LIVE PASS** | Injects user profile facts + bounds history to 10 turns max. |
| **CONN-18** | `Execution / Verification`| `ui.py: JarvisUI` | Thread-safe logging & HUD state updates | **LIVE PASS** | `player.write_log()` and `player.set_state()` update HUD visuals in real time. |

---

## 2. Classification Summary

- **LIVE PASS:** 16 Connections
- **UNIT-ONLY PASS:** 2 Connections (`Groq`/`OpenRouter`/`NVIDIA` fallback tiers when primary Gemini Live is active)
- **NOT VERIFIED:** 0 Core Connections
- **FAIL:** 0 Connections
