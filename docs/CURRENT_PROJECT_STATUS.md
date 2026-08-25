# INDUS (INDUS) — Current Project Status & Technical Inspection

**Inspection Date:** 2026-08-22  
**Target Platform:** Windows 10/11 (Python 3.11+, PyQt6, Google GenAI SDK, SoundDevice)  
**Inspection Type:** Full Codebase & Architecture Audit  

---

## 1. Current Project Structure

```text
INDUS-main/
├── main.py                     # [INTEGRATED / RUNTIME VERIFIED] Central Orchestrator & WebSocket Manager
├── ui.py                       # [INTEGRATED / RUNTIME VERIFIED] PyQt6 HUD Interface & Visualizer
├── or_client.py                # [INTEGRATED / RUNTIME VERIFIED] Dual-Engine LLM/LPU Client (Groq/OpenRouter/NVIDIA)
├── requirements.txt            # [INTEGRATED] Dependencies list
├── setup.py                    # [IMPLEMENTED] Packaging script
├── readme.md                   # Documentation
│
├── core/
│   ├── prompt.txt              # [INTEGRATED / RUNTIME VERIFIED] Master System Prompt & Operational Rules
│   ├── security_vault.py       # [INTEGRATED / TESTED] 4-digit PIN system
│   └── skip_ad.png             # [INTEGRATED / TESTED] OpenCV template for YouTube skip button
│
├── memory/
│   ├── db_engine.py            # [INTEGRATED / RUNTIME VERIFIED] SQLite database engine (indus_memory.db)
│   ├── memory_manager.py       # [INTEGRATED / RUNTIME VERIFIED] Keyword extractor & prompt context injector
│   ├── config_manager.py       # [IMPLEMENTED / PARTIAL] Legacy config loader
│   ├── indus_memory.db         # [RUNTIME VERIFIED] Active SQLite database
│   └── long_term.json          # [DUPLICATE / INACTIVE] Legacy JSON memory store
│
├── agent/
│   ├── planner.py              # [NOT INTEGRATED / ORPHANED] REST-based JSON multi-step planner
│   ├── executor.py             # [NOT INTEGRATED / ORPHANED] Python code execution agent
│   ├── error_handler.py        # [NOT INTEGRATED / ORPHANED] Static error analyzer & replanner
│   └── task_queue.py           # [PARTIALLY INTEGRATED] Priority task queue (imported but bypassed)
│
├── actions/                    # 30 Subsystem Modules
│   ├── audio_service.py        # [INTEGRATED / RUNTIME VERIFIED] SoundDevice mic stream & gain control
│   ├── autonomous_watcher.py   # [INTEGRATED / RUNTIME VERIFIED] Background system & theme monitor
│   ├── bluetooth_controller.py # [INTEGRATED / RUNTIME VERIFIED] Windows PnP dynamic Bluetooth manager
│   ├── browser_control.py      # [INTEGRATED / RUNTIME VERIFIED] Playwright + WebBrowser streaming controller
│   ├── code_helper.py          # [INTEGRATED / TESTED] Code generation & unit test helper
│   ├── computer_control.py     # [INTEGRATED / RUNTIME VERIFIED] PyAutoGUI mouse, scroll, keyboard & _screen_find
│   ├── computer_settings.py    # [INTEGRATED / RUNTIME VERIFIED] Win32 Gamma Ramp Brightness, PyCaw Volume, OS Settings
│   ├── deep_research.py        # [INTEGRATED / RUNTIME VERIFIED] Tavily + Gemini Grounded + DDG Research
│   ├── desktop.py              # [INTEGRATED / DUPLICATE] Wallpaper & desktop folder manager
│   ├── dev_agent.py            # [INTEGRATED / TESTED] Codebase scanner & refactoring agent
│   ├── file_controller.py      # [INTEGRATED / TESTED] File search, move & organizer
│   ├── file_processor.py       # [INTEGRATED / TESTED] Document & PDF text extractor
│   ├── flight_finder.py        # [INTEGRATED / TESTED] Flight price and route searcher
│   ├── game_updater.py         # [INTEGRATED / TESTED] Steam & game updater/launcher
│   ├── git_controller.py       # [INTEGRATED / TESTED] Git automated commits & shell terminal
│   ├── live_writer.py          # [INTEGRATED / TESTED] Auto-writer for Python code & notes to Desktop
│   ├── media_streamer.py       # [INTEGRATED / RUNTIME VERIFIED] Direct show mapper (SonyLIV, Hotstar, YouTube)
│   ├── mobile_bridge.py        # [INTEGRATED / TESTED] Android ADB wireless calls, SMS & battery
│   ├── open_app.py             # [INTEGRATED / RUNTIME VERIFIED] Direct OS protocol & Start launcher
│   ├── reminder.py             # [INTEGRATED / TESTED] Windows Task Scheduler manager
│   ├── screen_processor.py     # [INTEGRATED / TESTED] Dedicated Gemini vision live session
│   ├── security_protocols.py   # [INTEGRATED / TESTED] Screen lock, cloak & panic triggers
│   ├── send_message.py         # [INTEGRATED / TESTED] WhatsApp & Telegram text/call dispatcher
│   ├── shopping_assistant.py   # [INTEGRATED / RUNTIME VERIFIED] Amazon/Flipkart search + Safe checkout gate
│   ├── smart_home.py           # [INTEGRATED / TESTED] Smart home bulb/switch controller
│   ├── system_radar.py         # [INTEGRATED / TESTED] Hardware telemetry, Railways PNR & news
│   ├── wake_word.py            # [NOT INTEGRATED / ORPHANED] SpeechRecognition wake-word listener
│   ├── weather_report.py       # [INTEGRATED / TESTED] Open-Meteo weather fetcher
│   ├── web_search.py           # [INTEGRATED / TESTED] Gemini Grounded searcher
│   ├── workspace_teleport.py   # [INTEGRATED / TESTED] Windows snap layouts (split_dev, quad, focus)
│   └── youtube_video.py        # [INTEGRATED / RUNTIME VERIFIED] YouTube player, quality 360p-1080p, live ad-skip
│
├── config/
│   ├── api_keys.json           # [INTEGRATED / RUNTIME VERIFIED] Main key storage
│   └── smart_devices.json      # [INTEGRATED / TESTED] IoT configuration
│
└── docs/
    └── CURRENT_PROJECT_STATUS.md # Current Inspection Document
```

---

## 2. Existing Major Components & Status

| Component | Implemented Location | Integration Status | Tested Status | Runtime Verified | Primary Function |
|---|---|---|---|---|---|
| **Voice Orchestrator** | `main.py` (`JarvisLive`) | INTEGRATED | YES | YES | Bi-directional WebSocket streaming with Gemini Live API |
| **HUD GUI** | `ui.py` (`JarvisUI`, `MainWindow`) | INTEGRATED | YES | YES | PyQt6 Sci-Fi circular arc visualizer, real-time logging, metrics |
| **LLM / LPU Engine** | `or_client.py` (`OpenRouterClient`) | INTEGRATED | YES | YES | Multi-tier fallback (Groq LPU ➔ OpenRouter ➔ NVIDIA NIM) |
| **Long-Term Memory** | `memory/db_engine.py`, `memory_manager.py` | INTEGRATED | YES | YES | SQLite conversation logging & zero-cost keyword retrieval |
| **System Settings** | `actions/computer_settings.py` | INTEGRATED | YES | YES | Win32 Gamma Ramp Brightness (0-100%), PyCaw volume, Settings |
| **Vision & Click** | `actions/computer_control.py` (`_screen_find`) | INTEGRATED | YES | YES | Screenshot capture ➔ AI coordinate localization ➔ PyAutoGUI click |
| **Media Streamer** | `actions/media_streamer.py`, `youtube_video.py` | INTEGRATED | YES | YES | Direct show URLs + Live screen quality (360p-1080p) + Ad skipping |
| **Deep Research** | `actions/deep_research.py` | INTEGRATED | YES | YES | Real-time sports, release dates, tech facts synthesis |
| **Mobile ADB Bridge** | `actions/mobile_bridge.py` | INTEGRATED | YES | YES | Android wireless calls, SMS dispatch, battery monitoring |
| **Planner & Executor** | `agent/planner.py`, `agent/executor.py` | **NOT INTEGRATED** | NO | NO | Dead code (bypassed by Gemini Live native function calling) |
| **Wake Word Engine** | `actions/wake_word.py` | **NOT INTEGRATED** | NO | NO | Orphaned file (app uses open-mic stream) |

---

## 3. What Actually Works

1. **Full-Duplex Speech-to-Speech Streaming:** Native PCM 16kHz microphone stream to Gemini Live WebSocket and 24kHz audio playback via `sounddevice` with sub-second voice turnaround.
2. **Native Tool Calling (36 Tools):** Gemini server-side tool calls parsed and dispatched dynamically in `_execute_tool()` across 30 action modules.
3. **Universal Screen Brightness & Audio Volume:** Win32 Gamma Ramp adjusts hardware brightness on any external desktop monitor or laptop screen; PyCaw adjusts master system audio volume.
4. **YouTube Playback, Quality (360p-1080p) & Live Ad Skip:** Automatically navigates, clicks player controls, adjusts playback resolution, and skips on-screen ads via template + vision matching.
5. **Persistent Long-Term Memory:** Every conversation turn and user preference is automatically persisted to SQLite `indus_memory.db` without consuming API tokens during extraction.
6. **Deep Real-Time Research:** Multi-source facts aggregation (Tavily / Gemini Grounded / DuckDuckGo) for sports, upcoming release dates, and benchmarks.
7. **App & Protocol Launching:** Instant execution of Windows URIs (`ms-settings:`, `calc.exe`, `notepad.exe`) without search bar typing lag.

---

## 4. What Is Partially Implemented

1. **Task Queue (`agent/task_queue.py`):** The class `TaskQueue` is implemented with priorities and threading, and `get_queue()` is imported into `main.py`, but tools in `_execute_tool()` run directly in `loop.run_in_executor(None, ...)` rather than going through `TaskQueue.submit()`.
2. **Error Recovery (`agent/error_handler.py`):** Standalone error analyzer exists, but when a tool fails in `main.py`, the error string is simply returned to Gemini Live without triggering an automated retry/replanning loop.
3. **Screen Processor (`actions/screen_processor.py`):** Standalone Gemini Live vision session works, but does not communicate state back to the main voice session.

---

## 5. What Exists but Is Not Integrated (Dead / Orphaned Code)

1. **`agent/planner.py` (278 lines):** ReAct-style JSON step planner. Unused because `main.py` uses Gemini Live's native tool calling.
2. **`agent/executor.py` (400 lines):** Dynamic Python sandbox executor. Unused by runtime.
3. **`agent/error_handler.py` (197 lines):** Static error analyzer. Unused by runtime.
4. **`actions/wake_word.py` (122 lines):** `SpeechRecognition`-based wake-word detector. Unused because `main.py` operates on a continuous streaming audio loop.
5. **`memory/long_term.json`:** JSON file created during initial prototyping; now superseded by SQLite `indus_memory.db`.
6. **`memory/config_manager.py` (59 lines):** Helper methods superseded by direct `api_keys.json` loading in `main.py` and `or_client.py`.

---

## 6. Duplicate Implementations

1. **Desktop / Window Management:**
   - `actions/desktop.py` (457 lines) vs `actions/computer_settings.py` (801 lines) vs `actions/computer_control.py` (535 lines).
   - *Duplicate logic:* Window minimize/maximize, desktop folder operations, and shortcut simulations exist across all three files.
2. **Web Search:**
   - `actions/web_search.py` (Gemini Grounded Search) vs `actions/deep_research.py` (Tavily + Gemini + DDG).
3. **Audio Capture / Device Configuration:**
   - `actions/audio_service.py` vs `main.py` `_listen_audio` stream.
4. **Memory Storage:**
   - `memory/long_term.json` vs SQLite tables in `memory/indus_memory.db`.

---

## 7. Current Runtime Flow

### Actual Flow in Codebase:

```text
User Speaks
   ↓
Microphone Capture (sounddevice 16kHz PCM)
   ↓
WebSocket Stream (wss://generativelanguage.googleapis.com)
   ↓
Gemini 2.5 Flash Native Voice Reasoning
   ↓
[If Speech]: Audio PCM Chunks received ➔ Speaker Output (24kHz)
   ↓
[If Tool Call]: Gemini emits FunctionCall(name, args)
   ↓
main.py _execute_tool(name, args)
   ↓
Dispatched via loop.run_in_executor() to actions/*.py
   ↓
Action Execution (Win32, PyAutoGUI, WebBrowser, ADB, etc.)
   ↓
Result String returned to Gemini Live WebSocket
   ↓
Gemini speaks confirmation to User
   ↓
Background Thread writes conversation to SQLite (db_save_conversation)
```

### Gap vs Requested Flow:
- **Missing Steps in Runtime:**
  - There is **no explicit multi-step Planner** between intent comprehension and tool execution. Gemini Live decides the single tool call directly.
  - There is **no automated Verification step** (e.g. taking a screenshot to verify that a button click or window action actually took effect before reporting success).
  - There is **no automated Recovery loop** if a tool returns an error string (the error string is just read out by the AI).

---

## 8. Current Voice Capability

| Voice Feature | Status | Implementation Details |
|---|---|---|
| **Microphone Input** | ✅ Supported | `sounddevice.RawInputStream` (16kHz, 16-bit Mono PCM). |
| **Streaming Voice** | ✅ Supported | Full-duplex WebSocket stream to Gemini Live API. |
| **Speech Recognition** | ✅ Supported | Native end-to-end multimodal speech understanding (server-side). |
| **Text-to-Speech** | ✅ Supported | Native audio synthesis streamed as 24kHz raw PCM. |
| **Interruption / Barge-in** | ✅ Supported | Gemini server detects user speech; local audio output queue is cleared. |
| **Cancellation** | ⚠️ Partial | Mute toggle halts microphone stream; active background thread tools cannot be forcibly cancelled mid-flight. |
| **Wake Word** | ❌ Not Active | Code exists in `actions/wake_word.py`, but `main.py` runs in open-mic mode. |
| **Mic / Speaker Selection**| ✅ Supported | Configurable via `config/api_keys.json` and `actions/audio_service.py`. |
| **Non-blocking Audio** | ✅ Supported | PyAudio/SoundDevice callbacks and asyncio queues run off the GUI thread. |

---

## 9. Current Vision Capability

| Vision Feature | Status | Implementation Details |
|---|---|---|
| **Capture Screen** | ✅ Supported | `pyautogui.screenshot()` / `mss` / PIL. |
| **Read Screen Text / OCR** | ✅ Supported | Captured frame sent to Gemini 2.5 Flash / OpenRouter Vision. |
| **Understand Screen Content**| ✅ Supported | `actions/screen_processor.py` analyzes full desktop context. |
| **Identify UI Elements** | ✅ Supported | Natural language prompt in `_screen_find()` finds element labels. |
| **Locate Buttons** | ✅ Supported | Returns center coordinates `(x, y)`. |
| **Return Bounding Boxes** | ⚠️ Partial | Returns center point `(x, y)` only; does not return `(x, y, w, h)` bounding box. |
| **Perform Computer Action** | ✅ Supported | `pyautogui.click()`, `pyautogui.scroll()`, `pyautogui.write()`. |
| **Observe Result** | ❌ Missing | No post-action screenshot is taken automatically. |
| **Verify Action Success** | ❌ Missing | Does not visually verify if the UI state changed after a click. |

---

## 10. Current Memory Capability

- **Storage Medium:** Local SQLite database at `memory/indus_memory.db`.
- **Tables:** `conversations` (history & intent), `user_profile` (key-value facts), `app_habits` (launch frequency), `autonomous_rules`, `autonomous_log`.
- **Extraction:** Zero-cost regex/keyword classification (identity, preferences, shopping, habits, projects).
- **Injection:** Recent 25 conversation turns + user facts injected into system prompt on session reconnect.

---

## 11. Current Computer-Control Capability

- **Display Brightness:** Win32 `SetDeviceGammaRamp` (works on 100% of desktop external monitors & laptops) + WMI fallback.
- **Audio Control:** PyCaw master endpoint volume level (0-100%) and mute toggle.
- **Mouse & Keyboard:** PyAutoGUI clicking, typing, hotkey combinations, scrolling (scaled notches).
- **Application Management:** Direct protocol launching (`os.system('start ms-settings:')`) and Start menu search fallback.
- **Window Teleportation:** PowerShell Win32 `MoveWindow` scripts for `split_dev`, `quad`, `focus`.

---

## 12. Current UI Capability (PyQt6 `ui.py`)

- **Main Window:** Sci-Fi Iron Man HUD interface with circular `HudCanvas` Arc Reactor visualizer (60 FPS QTimer).
- **Live Logging:** `LogWidget` text stream displaying SYS, Tool, and Audio logs with auto-scroll.
- **System Telemetry:** Real-time CPU, RAM, GPU, and temperature metric bars.
- **Thread Safety:** All UI updates called from background threads use thread-safe methods / queues.
- **Responsiveness:** Long-running tool actions run in `loop.run_in_executor()`, preventing UI freezing.
- **Interactive Controls:** Mic Mute button, Text command input box, Settings overlay, File Drop Zone.

---

## 13. Current Security Capability

- **Startup Security Vault:** 4-digit PIN verification (`core/security_vault.py`).
- **Dangerous Action Confirmation:** System commands (`restart`, `shutdown`) require explicit `confirmed=yes` flag.
- **Payment Safety Gate:** E-commerce checkout tools (`proceed_to_cart_and_checkout`) halt before payment and demand explicit voice confirmation.
- **Anti-Hallucination Guardrails:** Prompt rules prevent false claims of modified passwords/PINs; password requests safely launch Windows Sign-in settings.

---

## 14. Test Results

- **Official Repository Tests:** `0` test files existed in `tests/`.
- **Scratch Audit Suite Execution:**
  - `verify_all.py`: **100% PASS** (All 36 tools AST syntax & imports valid).
  - `final_audit.py`: **9 / 9 PASS** (Deep research, Groq fallback, mobile bridge, live writer, workspace teleport, security vault, media streamer, shopping, main.py).
  - `test_transcript_fixes.py`: **5 / 5 PASS** (Brightness 10%, Windows settings launch, YouTube quality, password action).
  - `test_visual_actions.py`: **100% PASS** (Live screen ad-skip scan & visual quality changer).

---

## 15. Biggest Technical Problems

1. **Dead / Disconnected Architecture in `agent/`:**
   `agent/planner.py`, `agent/executor.py`, and `agent/error_handler.py` (over 850 lines of code) are completely bypassed and orphaned because `main.py` runs its own direct dispatch loop.
2. **Lack of Visual Closed-Loop Verification (Observe ➔ Verify ➔ Recover):**
   When INDUS clicks a button or triggers a UI change, it assumes success immediately without taking a follow-up screenshot to confirm that the expected UI state appeared.
3. **Duplicate Desktop / Window Actions:**
   Code for window snapping, mouse control, and wallpaper manipulation is fragmented across `actions/desktop.py`, `actions/computer_settings.py`, and `actions/computer_control.py`.
4. **No Formal Unit / Integration Test Suite:**
   There is no dedicated `tests/` directory with automated `pytest` suites to prevent regressions during future development.

---

## 16. Biggest Missing Capabilities

1. **Closed-Loop Action Verification:** Taking a screenshot after a mouse/keyboard action to verify that the target modal/window/state actually opened.
2. **Barge-in Tool Cancellation:** Inability to terminate an in-progress background executor task when the user interrupts with a new voice command.
3. **Structured Multi-Step Task Planning:** Seamlessly chaining 3+ interdependent tools (e.g., search product ➔ extract price ➔ write note ➔ send WhatsApp message) through a unified plan executor.

---

## 17. Recommended NEXT SINGLE FEATURE

### 🎯 **Closed-Loop Visual Action Verifier (`actions/action_verifier.py`)**

**Why this is the #1 single most important next feature:**  
Currently, INDUS performs screen clicks, window snapping, YouTube quality changes, and settings toggles "blindly" — it executes the click and immediately reports success to the user, even if the window was minimized, the button was obscured, or the popup failed to open.  
Implementing a lightweight **Closed-Loop Visual Action Verifier** will allow INDUS to:
1. Capture a post-action screenshot.
2. Verify that the intended UI change occurred.
3. Automatically retry or adjust coordinates if the action failed.
4. Provide 100% factual, verified feedback to the user.

---

## 18. Phase 8 — Advanced Real-Time Avatar System (COMPLETE)

- **Architecture:** Layered, modular avatar animation engine (`core/avatar/`).
- **Gaze Controller (`core/avatar/gaze.py`):** 9 discrete directions, continuous target tracking `[-1.0, 1.0]`, micro-saccades, and thinking wandering.
- **Blink Controller (`core/avatar/blink.py`):** Natural randomized biological blinking (3.5s - 6.5s interval, 180-220ms duration) with strict gaze preservation.
- **Lip-Sync Engine (`core/avatar/lipsync.py`, `core/avatar/audio.py`):** Low-latency 16kHz PCM audio RMS extraction, noise gate subtraction, attack/decay smoothing, and emotional mouth baseline co-existence.
- **Emotion Controller (`core/avatar/emotion.py`):** 10 emotional baseline expression profiles.
- **Visual FX & HUD (`core/avatar/fx.py`):** Cyberpunk HUD rings, scanlines, particles, state-reactive color aura.
- **Presentation Widget (`ui/avatar_widget.py`, `ui.py`):** 60 FPS non-blocking PyQt6 rendering with cursor tracking.
- **Developer Test Demo:** `scripts/test_avatar.py` (interactive hotkeys for emotions, gaze, blink, listening, thinking, speech).
- **Test Suite:** `tests/test_avatar_system.py` (20/20 PASS), `tests/test_ui_end_to_end.py` (18/18 PASS).
