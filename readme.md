# 🤖 INDUS (Mark-XXXIX)
### Autonomous Desktop AI Assistant & Military-Grade Cognitive Operating System
**Created by Ansh Kesharwani**

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![PyQt6](https://img.shields.io/badge/GUI-PyQt6%2060fps-brightgreen.svg)](https://www.riverbankcomputing.com/software/pyqt/)
[![Gemini 2.5 Live](https://img.shields.io/badge/AI-Gemini%202.5%20Live%20Native%20Audio-orange.svg)](https://ai.google.dev/)
[![Tests Passing](https://img.shields.io/badge/Tests-87%2F87%20Passed%20(100%25)-green.svg)](tests/run_all_tests.py)
[![Security Hardened](https://img.shields.io/badge/Security-Fail--Closed%204--Tier-red.svg)](core/security_engine.py)

---

## ✨ Overview

**INDUS** is an intelligent, female-voiced autonomous desktop AI assistant inspired by J.A.R.V.I.S. from Iron Man. It combines bidirectional real-time audio streaming, multimodal screen perception, computer vision UI grounding, Fail-Closed security, and persistent long-term SQLite memory into a unified desktop cognitive engine.

---

## 🚀 Key Architectural Highlights

* 🎙️ **Real-Time Voice Streaming**: Native bidirectional audio powered by Gemini 2.5 Live (16kHz input → 24kHz output) with sub-10ms interruption handling ("Stop", "Ruko").
* 👁️ **Computer Vision & UI Grounding**: Multi-tier visual grounding cascade (Local OCR <15ms → Geometry template match → Gemini 2.5 Flash VLM) with ActionVerifier state verification.
* 🛡️ **Fail-Closed 4-Tier Security Subsystem**: PBKDF2-HMAC salted PIN vault, AST python sandbox, action-target binding, and structured security audit logging.
* 🧠 **Persistent SQLite WAL Memory**: Automatic background fact extraction, conversation recall, app habits, and preference enforcement with 6,000-char context window protection.
* 🎨 **Hardware-Accelerated PyQt6 HUD**: 60fps holographic HUD with audio-reactive viseme lip sync, facial emotion state tracking, and floating info cards.
* 🛠️ **Unified Tool Registry**: 39 tools registered under a canonical dispatch pipeline for Voice, Text, and Autonomous Agent tasks.

---

## ⚡ Quick Start

### Option 1: One-Click Installer (Zero Python Setup)
Download INDUS_Setup_2026.exe from the latest release, run it, and follow the on-screen Setup Wizard.

### Option 2: Run from Source

1. **Clone the repository:**
   `ash
   git clone https://github.com/archanakesharwani27-prog/Indus.git
   cd Indus
   `

2. **Automated Setup (Windows):**
   `powershell
   PowerShell -ExecutionPolicy Bypass -File install.ps1
   `

3. **Configure API Keys:**
   Copy config/api_keys.example.json to config/api_keys.json and add your Gemini API key:
   `json
   {
       "gemini_api_key": "YOUR_API_KEY_HERE"
   }
   `

4. **Run Preflight Dependency Check:**
   `ash
   python scripts/preflight_check.py
   `

5. **Start INDUS:**
   `ash
   python main.py
   `

---

## 🧪 Test Suite

Run the master test runner across all 11 test suites:
`ash
python tests/run_all_tests.py
`
*(87 / 87 tests passing — 100% verified)*

---

## 📜 License & Attribution
Developed with ❤️ by **Ansh Kesharwani**.
