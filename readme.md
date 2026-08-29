<div align="center">

# ⚡ I.N.D.U.S. (Mark-XXXIX)
### **Intelligent Neural Desktop Universal System**
*Autonomous Military-Grade Desktop AI Assistant & Cognitive Operating System*

[![Python Version](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![GUI](https://img.shields.io/badge/GUI-PyQt6%2060FPS%20HUD-41CD52?style=for-the-badge&logo=qt&logoColor=white)](https://www.riverbankcomputing.com/software/pyqt/)
[![AI Engine](https://img.shields.io/badge/AI-Gemini%202.5%20Live%20Native%20Audio-FF6F00?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev/)
[![Security](https://img.shields.io/badge/Security-Fail--Closed%204--Tier-E53935?style=for-the-badge&logo=security&logoColor=white)](core/security_engine.py)
[![Tests](https://img.shields.io/badge/Tests-87%2F87%20Passed%20(100%25)-00C853?style=for-the-badge&logo=githubactions&logoColor=white)](tests/run_all_tests.py)
[![Status](https://img.shields.io/badge/Status-Production%20Ready-00E5FF?style=for-the-badge)](https://github.com/archanakesharwani27-prog/Indus)

<p align="center">
  <b>Developed with ❤️ by Ansh Kesharwani</b><br>
  <i>An autonomous desktop intelligence that can hear, see, speak, plan, and control your OS in real-time.</i>
</p>

---

</div>

## 🌌 System Overview

**INDUS (Mark-XXXIX)** is a next-generation desktop cognitive assistant engineered with full hardware-accelerated visual grounding, low-latency bidirectional voice streaming, and closed-loop task execution.

Unlike standard chatbot wrappers, **INDUS** operates as an autonomous agent directly inside your operating system:
* **Sees** what is on your screen using OCR token extraction and Multimodal VLM grounding.
* **Hears & Speaks** simultaneously using Gemini 2.5 Live Native WebSockets audio with sub-10ms interruption handling (*"Stop", "Ruko", "Cancel"*).
* **Executes & Verifies** workflows across 39 system tools using state diffing and perceptual hashing.
* **Remembers** everything in a persistent SQLite WAL database with automated fact extraction.
* **Protects** your computer using a 4-tier Fail-Closed security gate and PBKDF2 PIN vault.

---

## 🏛️ Architecture & Data Flow

`
                              ┌─────────────────────────┐
                              │     User Interaction    │
                              │ (16kHz Audio / Keyboard)│
                              └────────────┬────────────┘
                                           │
                                           ▼
                              ┌─────────────────────────┐
                              │  PyQt6 60fps HUD Avatar │
                              │ (Gaze, Visemes, Emotion)│
                              └────────────┬────────────┘
                                           │
                                           ▼
                              ┌─────────────────────────┐
                              │   Gemini 2.5 Live Audio │
                              │ (Sub-10ms Barge-in Gate)│
                              └────────────┬────────────┘
                                           │
                                           ▼
    ┌────────────────────────────────────────────────────────────────────────┐
    │                        CANONICAL TOOL REGISTRY                         │
    │                      (39 Deep Automation Actions)                      │
    └──────┬──────────────────┬──────────────────┬────────────────────┬──────┘
           │                  │                  │                    │
           ▼                  ▼                  ▼                    ▼
    ┌──────────────┐   ┌──────────────┐   ┌──────────────┐    ┌──────────────┐
    │    Vision    │   │  OS Control  │   │  Developer   │    │  Web/Media   │
    │  & Grounding │   │  & Hardware  │   │   & Tasks    │    │  & Research  │
    └──────┬───────┘   └──────┬───────┘   └──────┬───────┘    └──────┬───────┘
           │                  │                  │                    │
           └──────────────────┴─────────┬────────┴────────────────────┘
                                        │
                                        ▼
                         ┌─────────────────────────────┐
                         │ Fail-Closed Security Engine │
                         │ (DESTRUCTIVE / HIGH / PIN)  │
                         └──────────────┬──────────────┘
                                        │
                                        ▼
                         ┌─────────────────────────────┐
                         │       ActionVerifier        │
                         │ (Screen Diff / State Check) │
                         └──────────────┬──────────────┘
                                        │
                                        ▼
                         ┌─────────────────────────────┐
                         │   SQLite Long-Term Memory   │
                         │ (WAL Mode / Fact Extractor) │
                         └─────────────────────────────┘
`

---

## 🔥 Key Subsystems & Features

### 1. 🎙️ Real-Time Voice Pipeline
* **Gemini 2.5 Flash Native Audio Preview**: Direct bidirectional 16kHz audio input and 24kHz audio output.
* **Sub-10ms Barge-In Interruption**: Say *"Stop"*, *"Ruko"*, or *"Cancel"* mid-speech to immediately halt any ongoing task.
* **Phoneme-to-Viseme Lip Sync**: Converts live spoken audio into real-time mouth shapes and facial animations.

### 2. 👁️ Multi-Tier Computer Vision Engine
* **Tier 1 (Fast OCR)**: Pytesseract token bounding-box matching in <15ms.
* **Tier 2 (Template Match)**: Geometric and icon matching in <25ms.
* **Tier 3 (Multimodal VLM)**: Gemini 2.5 Flash Visual Grounding for complex dynamic UIs.
* **ActionVerifier**: Compares pre- and post-action screen snapshots using perceptual hashing to guarantee execution success.

### 3. 🛡️ Fail-Closed Security Subsystem
* **4-Tier Risk Matrix**:
  - DESTRUCTIVE: Drive formatting, mass deletion, registry alterations (Requires PIN Vault auth).
  - HIGH: Terminal execution, software installations, system settings changes.
  - MEDIUM: File modifications, app control.
  - LOW: Screen understanding, read-only search, reminders.
* **Salted PBKDF2 Vault**: 3-attempt lockout gate for privileged commands.
* **AST Python Sandbox**: Safe evaluation of dynamically generated scripts.
* **Credential Redactor**: Automatically masks API keys and tokens in all audit logs.

### 4. 🧠 Long-Term Memory & Habit Learning
* **SQLite Database (WAL Mode)**: Thread-safe persistent storage for conversations, user identity, app habits, and autonomous rules.
* **Async Fact Extraction**: Background worker detects preferences and habits automatically.
* **Token Safe Injection**: Memory prompt bounded with a 6,000-character safety limit to prevent token overflows.

---

## 🛠️ Complete Tool Capability Matrix (39 Modules)

| Category | Tools & Handlers | Description |
|---|---|---|
| **OS & Desktop** | open_app, desktop_control, computer_control, computer_settings | Control windows, click buttons, change system volume/brightness, launch apps |
| **Vision & Screen** | screen_understand, vision_click,vision_type, vision_scroll, vision_engine | Ground UI coordinates, read text on screen, click anywhere visually |
| **Web & Research** | deep_research, web_search, rowser_control, light_finder | Multi-source DuckDuckGo/Tavily research, browse web, compare flights |
| **Media & Audio** | stream_content, youtube_video, video_editor, universal_ad_skipper | Stream movies, autonomous YouTube navigation, FFmpeg video editing, skip video ads |
| **Developer Tools**| code_helper, dev_agent, git_controller, 	terminal_command, live_writer | Write code, run CLI commands, git version control, live desktop note generation |
| **Hardware & IoT** | mobile_bridge, luetooth_control, smart_home | Android ADB wireless bridge (calls, SMS, battery), bluetooth devices, smart lights |
| **System Security**| security_vault, security_protocols, system_radar | Manage PBKDF2 PIN, execute emergency protocols, monitor running processes |
| **Shopping & Daily**| search_and_show_products, proceed_to_cart_and_checkout, 
reminder| Search e-commerce deals, automate checkout steps, set scheduled alarms |

---

## ⚡ Quick Start & Installation

### 🚀 Option A: One-Click GUI Installer (No Python Needed)
1. Download INDUS_Setup_2026.exe from the latest release.
2. Double-click the installer, paste your Gemini API key , and click **Install**.
3. Launch INDUS directly from your Desktop shortcut!

### 💻 Option B: Run from Source (Developers)

#### 1. Clone the repository
`bash
git clone https://github.com/archanakesharwani27-prog/Indus.git
cd Indus
`

#### 2. Run the automated dependency installer (Windows)
`powershell
PowerShell -ExecutionPolicy Bypass -File install.ps1
`

#### 3. Set up your API Keys
Copy config/api_keys.example.json to config/api_keys.json:
`json
{
    "gemini_api_key": "YOUR_GEMINI_API_KEY_HERE",
    "openrouter_api_key": "",
    "groq_api_key": ""
}
`

#### 4. Run the preflight hardware & dependency check
`bash
python scripts/preflight_check.py
`

#### 5. Launch INDUS
`bash
python main.py
`

---

## 🧪 Verification & Test Suite

INDUS comes with a complete regression test suite verifying all 11 core subsystems:

`bash
python tests/run_all_tests.py
`

`	ext
======================================================================
  INDUS (INDUS) — MASTER PRODUCTION VERIFICATION RUNNER
======================================================================
Ran 87 tests in 152.477s

  TOTAL TESTS RUN : 87
  PASSED          : 87 / 87 (100.0%)
  FAILURES        : 0
  ERRORS          : 0
  STATUS          : OK
======================================================================
`

---

## 📁 Repository Structure

`	ext
INDUS/
├── actions/             # 39 Canonical Action Modules (Vision, OS, ADB, Media, Research)
├── agent/               # Closed-Loop Agent Planner, Error Handler, Task Model
├── assets/              # Avatar Face Expressions (Happy, Angry, Thinking, Calm, etc.)
├── config/              # Configuration & Device Profiles (API key templates)
├── core/                # Security Engine, Tool Registry, Viseme Timeline, Event Bus
├── docs/                # Architectural Documentation, Audits & Specifications
├── memory/              # SQLite Database Engine, Fact Extraction & Habit Tracker
├── scripts/             # Setup Wizard (installer.py), Preflight Checker (preflight_check.py)
├── tests/               # 11 Unit & Integration Test Suites (87 Tests)
├── indus.spec           # PyInstaller Specification for Standalone EXE
├── install.ps1          # One-Click Dependency Installer
├── main.py              # Application Entry Point & Gemini 2.5 Live Pipeline
├── requirements.txt     # Pinned Python Dependencies
└── ui.py                # Hardware-Accelerated PyQt6 Holographic HUD & Visualizer
`

---

## 👤 Author & Credits

* **Lead Architect & Developer:** **Ansh Kesharwani**
* **Project Name:** Project INDUS (Mark-XXXIX)
* **GitHub Repository:** [archanakesharwani27-prog/Indus](https://github.com/archanakesharwani27-prog/Indus)

---

<div align="center">
  <sub>Built for the future of human-computer interaction. Powered by Google Gemini 2.5 & Advanced Agentic Intelligence.</sub>
</div>
