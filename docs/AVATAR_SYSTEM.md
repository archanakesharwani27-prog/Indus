# INDUS Advanced Real-Time Avatar System — Technical Manual

## 1. Executive Summary

The **INDUS Avatar System** is a real-time, modular, 60 FPS AI character animation and rendering engine developed for the INDUS personal assistant. It transforms static HUD portraits into a living AI character with smooth 9-directional eye gaze, cursor/target following, randomized natural blinking, voice-driven smoothed lip-synchronization, and emotion-reactive facial dynamics.

---

## 2. Architecture & Layered Decoupling

```
                           INDUS BRAIN / MAIN
                                   │
                 ┌─────────────────┼─────────────────┐
                 ▼                 ▼                 ▼
              Emotion            Intent            Speech
                 │                                   │
                 │                                   ▼
                 │                              Audio Stream
                 │                               (PCM chunks)
                 │                                   │
                 ▼                                   ▼
        EventBus / Direct API                   LipSync Engine
                 │                                   │
                 └─────────────────┬─────────────────┘
                                   ▼
                            AvatarController
                                   │
       ┌───────────────┬───────────┼───────────────┬───────────────┐
       ▼               ▼           ▼               ▼               ▼
    Emotion          Gaze        Blink          LipSync        Avatar FX
  Controller      Controller  Controller      Controller      Controller
       │               │           │               │               │
       └───────────────┴───────────┼───────────────┴───────────────┘
                                   ▼
                           AvatarState Model
                                   │
                                   ▼
                             AvatarRenderer
                                   │
                    ┌──────────────┼──────────────┐
                    ▼              ▼              ▼
                 BaseFace        Eyes           Mouth
                 (+ Glow)     (+ Eyelids)     (+ Baseline)
                                   │
                                   ▼
                          PyQt6 AvatarWidget
                            (Presentation)
```

- **Zero UI Blocking**: All physics, easing curves, audio RMS calculations, and state interpolations are computed in sub-millisecond math routines. The PyQt6 UI merely draws the current `AvatarState` onto the canvas during `paintEvent`.
- **Modular Sub-Controllers**:
  - `EmotionController` (`core/avatar/emotion.py`): 10 emotional baselines.
  - `GazeController` (`core/avatar/gaze.py`): 9 cardinal/diagonal directions, continuous normalized tracking `[-1.0, 1.0]`, micro-saccades, and thinking wandering.
  - `BlinkController` (`core/avatar/blink.py`): Randomized natural blinking (3.5s – 6.5s interval, 180–220ms duration) with strict gaze preservation.
  - `LipSyncController` (`core/avatar/lipsync.py`): Real-time RMS audio energy extraction, noise gating, attack/decay smoothing, and emotion-mouth coexistence.
  - `AvatarFXController` (`core/avatar/fx.py`): Cyberpunk HUD rings, scanlines, particle dynamics, and reactive state glows.
  - `AvatarRenderer` (`core/avatar/renderer.py`): 5-layer composited graphics pipeline.

---

## 3. State Models & Enums

### Emotions (`EmotionType`):
- `NEUTRAL`, `HAPPY`, `SAD`, `THINKING`, `SURPRISED`, `ANGRY`, `CONFUSED`, `CONCERNED`, `CALM`, `EXCITED`.

### Operational States (`OperationalState`):
- `IDLE`, `LISTENING`, `THINKING`, `SPEAKING`, `PROCESSING`, `SUCCESS`, `WARNING`, `ERROR`, `STANDBY`, `MUTED`.

### Gaze Directions (`GazeDirection`):
- `CENTER`, `LEFT`, `RIGHT`, `UP`, `DOWN`, `UP_LEFT`, `UP_RIGHT`, `DOWN_LEFT`, `DOWN_RIGHT`, `CUSTOM`.

### Mouth Shapes (`MouthShape`):
- `CLOSED`, `SLIGHT`, `MEDIUM`, `WIDE`.

---

## 4. Public API Reference

```python
from core.avatar import AvatarController, EmotionType, GazeDirection

avatar = AvatarController()

# Set Emotion
avatar.set_emotion(EmotionType.HAPPY)     # Smooth transition to smiling baseline

# Gaze & Cursor Tracking
avatar.look_direction(GazeDirection.RIGHT)# Look right
avatar.look_at(x=0.5, y=-0.3)             # Look at normalized coordinate
avatar.look_center()                      # Return to center
avatar.follow_cursor(screen_x, screen_y, width, height)
avatar.look_at_vision_target(x, y, w, h)  # Look at vision bounding box

# Blinking
avatar.start_blink()                      # Natural blink preserving gaze

# Operational States & Voice Lip-Sync
avatar.set_listening(True)                # Listening state
avatar.set_thinking(True)                 # Thinking state (wandering upward gaze)
avatar.start_speaking()                   # Speaking state
avatar.process_audio_chunk(pcm_bytes)     # Ingest live 16kHz audio buffer
avatar.stop_speaking()                    # Smooth mouth closure
avatar.reset_to_idle()                    # Reset to idle neutral
```

---

## 5. Developer Interactive Demo

To test and preview all avatar capabilities interactively without requiring an API key:

```powershell
python scripts/test_avatar.py
```

### Hotkeys:
- `1 - 5`: Switch emotions (Neutral, Happy, Sad, Thinking, Surprised)
- `W / A / S / D`: Look Up, Left, Down, Right; `C`: Center
- `B`: Trigger natural biological blink
- `L`: Listening mode (Electric Cyan)
- `T`: Thinking mode (Amber pulse + upward gaze wander)
- `SPACE`: Simulate speaking & real-time lip-sync with synthetic PCM audio waves
- Mouse movement: Dynamic eye gaze cursor following

---

## 6. Automated Test Suite

Run the dedicated test suite verifying all 20 test specifications:

```powershell
python -m pytest tests/test_avatar_system.py -v
```

All 20 unit tests and 18 E2E regression tests pass with 100% success.
