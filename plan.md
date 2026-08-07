# Indus - JARVIS Implementation Plan

## Vision
A fully-featured personal AI assistant (like Iron Man's JARVIS) with:
- System control (Windows + Android)
- Long-term semantic memory (years of data)
- Computer vision (screen analysis, face recognition)
- Voice interaction (STT + TTS + wake word)
- Proactive intelligence

## Architecture Decisions
- **Hybrid**: Local Python orchestration + Cloud APIs (NVIDIA/Gemini, OpenAI Whisper/TTS)
- **Voice**: OpenAI Whisper (STT) + OpenAI TTS
- **Android**: Custom Kotlin app + WebSocket bridge
- **Memory**: SQLite (hot) + Qdrant (vector) + NetworkX (knowledge graph)
- **LLM Providers**: NVIDIA (Nemotron), Gemini, Mock

## Phase Overview

| Phase | Duration | Focus | Key Deliverable | Status |
|-------|----------|-------|-----------------|--------|
| 1 | Done | Core chat + memory | Text CLI with persistent memory | ✅ **COMPLETE** |
| 2 | 3 weeks | Voice + Intent | Voice mode with wake word | ✅ **COMPLETE** |
| 3 | 3 weeks | System Control | Windows app/window/shell control | ✅ **COMPLETE** |
| 4 | 3 weeks | Android Bridge | Full phone control from PC | ✅ **PC-side COMPLETE** |
| 5 | 4 weeks | Semantic Memory | Year-long recall + semantic search | ✅ **COMPLETE** |
| 6 | 4 weeks | Vision | Screen understanding + face ID | ✅ **COMPLETE** |
| 7 | 4 weeks | Proactive + GUI | Suggestions + Tauri dashboard | ✅ **COMPLETE** |
| 8 | 4 weeks | Agent Workflows | Plan → Execute → Verify agents | ✅ **COMPLETE** |
| 9 | 4 weeks | Multi-Agent | Collaborative agent teams | ✅ **COMPLETE** |
| 10 | 4 weeks | Production Ready | Real APIs, voice streaming, GUI | 🔄 **IN PROGRESS** |

**Total: ~33 weeks (8 months part-time)**

## Phase Dependencies
```
Phase 1 (Done)
    |
    v
Phase 2 (Voice + Intent) ---------+
    |                             |
    v                             v
Phase 3 (System)            Phase 4 (Android)
    |                             |
    +-------------+-----------------+
                  |
                  v
            Phase 5 (Semantic Memory)
                  |
                  v
            Phase 6 (Vision)
                  |
                  v
            Phase 7 (Proactive + GUI)
                  |
                  v
            Phase 8 (Agent Workflows)
                  |
                  v
            Phase 9 (Multi-Agent Collaboration)
```

## Current Status: Phase 9 Complete - Multi-Agent Collaboration & Advanced Features

### ✅ Phase 9 Complete - Multi-Agent Collaboration & Advanced Features

**Modules Created:**
- `core/multiagent/base.py` - BaseAgent, AgentConfig, AgentRole, AgentCapability, AgentMessage, MessageType, AgentMessageBus, SharedState
- `core/multiagent/agents.py` - ResearcherAgent, PlannerAgent, ExecutorAgent, VerifierAgent, CoordinatorAgent, CriticAgent, SummarizerAgent, create_default_team()
- `core/multiagent/orchestrator.py` - MultiAgentOrchestrator, MultiAgentWorkflow, WorkflowStep, WorkflowPattern
- `core/multiagent/__init__.py` - Package exports
- `core/skills/multiagent.py` - 6 multi-agent skills (run_workflow, list_workflows, team_status, delegate, custom_workflow, shared_state)

**Multi-Agent Skills Working (6):**
- `multiagent.run_workflow` - Run multi-agent workflow (research_plan_execute_verify, plan_execute_verify, parallel_research, debate)
- `multiagent.list_workflows` - List available workflows
- `multiagent.team_status` - Show agent team status
- `multiagent.delegate` - Delegate task to specific agent role
- `multiagent.custom_workflow` - Run custom workflow with defined steps
- `multiagent.shared_state` - Manage shared state between agents

**Built-in Workflows (4):**
1. `research_plan_execute_verify` - Full cycle: Research → Plan → Execute → Verify
2. `plan_execute_verify` - Plan → Execute → Verify (no research)
3. `parallel_research` - Parallel research from multiple angles
4. `debate` - Pro/Con debate with synthesis

**Agent Team (7 specialized agents):**
- **Coordinator** - Orchestrates the team, delegates tasks, monitors progress
- **Planner** - Creates and refines execution plans using TaskPlanner
- **Researcher** - Gathers information (web search, memory, screen analysis)
- **Executor** - Executes plans and actions via PlanExecutor
- **Verifier** - Verifies results and validates plans via ResultVerifier
- **Critic** - Critiques plans and outputs for flaws/risks
- **Summarizer** - Summarizes outputs and extracts key points

**Communication Infrastructure:**
- **AgentMessageBus** - Central message bus with request/response, broadcast, role-based routing
- **SharedState** - Thread-safe shared state with subscriptions and locking
- **AgentMessage** - Structured messages with correlation IDs for request/response

**Architecture:**
```
User Goal → Coordinator → [Researcher] → [Planner] → [Executor] → [Verifier]
                    ↓                              ↓
              [Critic] ←───────────────────── [Summarizer]
                    ↓
            Shared State (cross-agent memory)
```

**Key Features:**
- Dependency-aware workflow execution with parallelization support
- Multiple workflow patterns (sequential, parallel, debate, map-reduce)
- Inter-agent communication via message bus with request/response
- Shared state for cross-agent knowledge sharing
- LLM-powered agents with fallback to heuristic methods
- Custom workflow definition via JSON
- Progress callbacks for UI integration
- Skill registry integration (all system/web/memory/vision/agent skills available)

**Tests:** 29/29 Phase 9 tests pass

### 🔄 Next: Phase 10 - Advanced Features & Production Hardening
- GUI Dashboard (Tauri/Rust) with real-time agent visualization
- Plugin marketplace for community skills
- Android app completion (phone-side)
- Multi-modal input (vision + voice + text)
- Long-running background agents
- Agent memory persistence across sessions
- Distributed agent deployment

### ✅ Phase 1 Complete - Core Brain
- SQLite memory with persistent conversation history
- LLM provider abstraction (Gemini, Mock, **NVIDIA added**)
- ChatEngine with context management
- All 6 tests passing

### ✅ Phase 2 Complete - Voice + Intent System
**Modules Created:**
- `core/voice/stt.py` - WhisperClient (OpenAI API)
- `core/voice/tts.py` - TTSClient (OpenAI API)
- `core/voice/wake_word.py` - WakeWordDetector (Porcupine) + SimpleWakeWordDetector
- `core/voice/audio_io.py` - AudioStream + StreamingAudioInput
- `core/intent/parser.py` - IntentParser (provider-agnostic function calling)
- `core/intent/registry.py` - SkillRegistry
- `core/intent/executor.py` - IntentExecutor (dispatch + confirm)
- `core/skills/base.py` - BaseSkill + SkillDefinition
- `core/skills/system.py` - 9 system skills
- `core/skills/web.py` - 4 web skills
- `core/skills/communication.py` - 5 communication stubs

**Skills Working:**
- `system.open_app` - Launch apps
- `system.run_command` - PowerShell/CMD (with confirmation)
- `system.volume_control` - Volume get/set/mute/up/down ✅
- `system.list_windows` / `system.focus_window` / `minimize` / `maximize` ✅
- `system.screenshot` / `system.read_screen` (OCR) ✅
- `web.open_url` / `web.search` / `web.youtube_play` / `web.youtube_music`
- Communication stubs (WhatsApp, calls, SMS - Phase 4)

### ✅ Phase 3 Complete - System Control
**Modules Created:**
- `core/system/launcher.py` - AppLauncher (registry, PATH, Start Menu scanning)
- `core/system/windows.py` - WindowManager (focus, minimize, maximize, close, move)
- `core/system/shell.py` - ShellExecutor (allowlist/blocklist, audit log)
- `core/system/screen.py` - ScreenAnalyzer (mss capture + Tesseract/Gemini Vision OCR)

**Skills Working:**
- All 9 system skills tested and functional
- App discovery from registry, PATH, Start Menu
- Window management (list, focus, minimize, maximize, close)
- Safe shell execution with security policies
- Screen capture + OCR (Tesseract local)
- Volume control via pycaw

### ✅ Phase 4 - Android Bridge (PC-side COMPLETE)
**PC Modules Created:**
- `core/android/bridge.py` - WebSocket client (request/response, auto-reconnect, notifications)
- `core/android/device.py` - DeviceManager (discovery, PIN/QR pairing, connection management)
- `core/android/skills.py` - 11 Android skills
- `core/android/async_helper.py` - Background event loop for sync skill execution

**Android Skills Working (PC-side tested with mock server):**
- `android.open_app` - Launch app on phone (package name)
- `android.tap` / `android.swipe` / `android.type_text` - UI control
- `android.get_notifications` - Read phone notifications
- `android.media_control` - Play/pause/next/previous/stop
- `android.answer_call` / `android.decline_call` - Call handling
- `android.open_youtube` - YouTube search/play
- `android.screenshot` - Phone screenshot
- `android.device_info` - Device details

**Pairing Flow Ready:**
- Device discovery via UDP broadcast
- 6-digit PIN pairing
- QR code data generation
- Persistent WebSocket with auto-reconnect

**Android App (Kotlin) - STRUCTURE CREATED:**
```
android_app/
|-- app/
|   |-- src/main/
|   |   |-- AndroidManifest.xml ✅ (all permissions)
|   |   |-- java/com/indus/droid/
|   |   |   |-- IndusApplication.kt ✅
|   |   |   |-- model/WsModels.kt ✅ (serialization)
|   |   |   |-- accessibility/AccessibilityService.kt ✅ (tap/swipe/type)
|   |   |   |-- notification/NotificationListenerService.kt ✅
|   |   |   |-- websocket/WebSocketService.kt ✅ (Ktor client, foreground service)
|   |   |   |-- pairing/PairingActivity.kt ✅ (PIN/QR UI)
|   |   |   |-- ui/MainActivity.kt ✅ (settings, status)
|   |   |   |-- BootReceiver.kt ✅ (auto-start)
|   |   |-- res/ (layouts, strings, colors, themes, menus)
|   |-- build.gradle.kts ✅ (Ktor, Coroutines, Serialization)
|   |-- settings.gradle.kts ✅
|-- build.gradle.kts ✅
```

### ✅ Phase 5 Complete - Semantic Long-Term Memory
**Modules Created:**
- `core/memory/vector_store.py` - VectorStore (Qdrant, ChromaDB, Mock)
- `core/memory/knowledge_graph.py` - KnowledgeGraph (NetworkX + SQLite)
- `core/memory/semantic.py` - SemanticMemory (search, temporal recall, summaries)
- `core/memory/consolidation.py` - MemoryConsolidator (background job)
- `core/memory/__init__.py` - Package exports

**Skills Working (7):**
- `memory.search` - Semantic search across all history
- `memory.recall_date` - "What happened on 2025-08-02?" / "yesterday"
- `memory.recall_week` - "What happened last week?"
- `memory.recall_month` - "What happened last month?"
- `memory.get_summary` - AI summary: "Summarize last week"
- `memory.learn_fact` - Explicit fact storage ("Remember I like dark mode")
- `memory.stats` - System statistics

**Architecture:**
```
Hot Memory (SQLite)      →  Recent N messages (Phase 1)
    ↓ consolidation (60 min)
Warm Memory (Vector DB)  →  Embeddings for semantic search (NEW)
    ↓ extraction (LLM)
Cold Memory (Knowledge Graph) → Entities, relations, facts (NEW)
```

**Background Consolidation:**
- Runs every 60 minutes via `schedule` library
- Extracts entities/relations using LLM function calling
- Creates embeddings via OpenAI/Gemini/Mock providers
- Temporal indexing: date/week/month/year keys

**Tests:** 6/6 Phase 1 tests pass (backward compatible)
**Manual Verified:** All 7 memory skills working

**Dependencies Added:** `qdrant-client`, `chromadb`, `networkx`, `schedule`

### ✅ Phase 8 Complete - Agent Workflows (Plan → Execute → Verify)

**Modules Created:**
- `core/agents/base.py` - Agent, AgentStep, AgentPlan, AgentResult, AgentStatus
- `core/agents/workflow.py` - AgentWorkflow, WorkflowManager
- `core/agents/planner.py` - TaskPlanner (LLM + heuristic planning)
- `core/agents/executor.py` - PlanExecutor (step execution with dependency resolution)
- `core/agents/verifier.py` - ResultVerifier (LLM + rule-based verification)
- `core/agents/__init__.py` - Package exports
- `core/skills/agent.py` - 6 agent skills (plan, execute, verify, run, status, list_workflows)

**Agent Skills Working (6):**
- `agent.plan` - Create execution plan for a goal
- `agent.execute` - Execute a plan
- `agent.verify` - Verify plan results
- `agent.run` - Full workflow: plan → execute → verify
- `agent.status` - Get workflow status
- `agent.list_workflows` - List registered workflows

**Architecture:**
```
User Goal → TaskPlanner → AgentPlan (steps with dependencies)
    ↓
PlanExecutor → Execute steps in dependency order
    ↓
ResultVerifier → Verify goal achieved (LLM + rules)
    ↓
Retry on failure (configurable)
```

**Key Features:**
- Dependency-aware step execution (parallelizable)
- LLM-based planning with fallback to heuristics
- LLM-based verification with rule-based fallback
- Automatic retry on failure
- Progress callbacks for UI integration
- Multiple workflow support via WorkflowManager

**Tests:** 21/21 Phase 8 tests pass (5 skipped - require NVIDIA_API_KEY)

### 🔄 Next: Phase 9 - Multi-Agent Collaboration & Advanced Features