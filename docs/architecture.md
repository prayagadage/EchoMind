# EchoMind System Architecture Specification

## Overview

EchoMind is a local-first, offline AI meeting assistant engineered specifically for macOS Apple Silicon (MacBook Air M2, 16 GB RAM). The application continuously captures local microphone and system audio, transcribes multilingual speech (Marathi, Hindi, English), translates input into English, monitors audio streams for specific keyword triggers (e.g. `"Prayag"`), and generates live streaming summaries as well as structured final meeting notes.

---

## Architectural Principles

1. **Strict Offline Execution & Privacy**: All processing runs locally on device. No audio or transcript data ever leaves the host machine.
2. **Layered Separation of Concerns (SOLID)**:
   - **`core/`**: Infrastructure, logging, configuration schemas, constants, base exceptions.
   - **`modules/`**: High-cohesion domain sub-packages decoupled via explicit interfaces.
   - **`app/`**: Container lifecycle management, bootstrap routines, dependency wiring.
   - **`ui/`**: User interface controllers (CLI & future native macOS GUI).
3. **Apple Silicon Hardware Acceleration**: Designed to leverage Apple Neural Engine (ANE) and Metal GPU performance via Metal Performance Shaders (MPS) and MLX frameworks in future AI phases.
4. **Scalability up to 50,000+ Lines of Code**: Strict type hints, modular sub-package architecture, zero circular imports, and clean dependency inversion.

---

## System Component Diagram

```
+--------------------------------------------------------------------------+
|                            USER INTERFACE LAYER                          |
|                    (ui/cli.py / Native macOS GUI)                        |
+------------------------------------+-------------------------------------+
                                     |
                                     v
+------------------------------------+-------------------------------------+
|                          APPLICATION LAYER                               |
|                  ApplicationContainer (app/container.py)                 |
+------------------------------------+-------------------------------------+
                                     |
                                     v
+------------------------------------+-------------------------------------+
|                       AUDIO & DOMAIN MODULES                             |
|                                                                          |
|  +--------------------+                                                  |
|  | sounddevice Stream | (CoreAudio PCM float32)                          |
|  +---------+----------+                                                  |
|            |                                                             |
|            v                                                             |
|  +---------+----------+      +-------------------+                       |
|  |    AudioEngine     | ---> |    AudioBuffer    | (In-Memory Ring)      |
|  +---------+----------+      +-------------------+                       |
|            |                                                             |
|            v (AudioChunk)                                                |
|  +---------+----------+                                                  |
|  |     EventBus       | (Pub/Sub Router)                                 |
|  +----+----+-----+----+                                                  |
|       |    |     |                                                       |
|       v    v     v                                                       |
|  +----+----+-----+----------------------------------------------------+  |
|  |             STT TranscriptionPipeline (Phase 2)                    |  |
|  |             (MLX Whisper -> TranscriptEvent)                       |  |
|  +------------------------------+-------------------------------------+  |
|                                 |                                        |
|                                 v (TranscriptEvent)                      |
|  +------------------------------+-------------------------------------+  |
|  |               INDEPENDENT WORKER EVENT ROUTER                      |  |
|  |                                                                    |  |
|  |                 AudioChunk / TranscriptEvent                       |  |
|  |                               │                                    |  |
|  |        ┌──────────────────────┼──────────────────────┐             |  |
|  |        ▼                      ▼                      ▼             |  |
|  | Translation Worker    AlertManager Worker    SpeakerService Worker |  |
|  | (modules/translation) (modules/intelligence)      (modules/speaker)    |  |
|  |        │                      │                      │             |  |
|  |        ▼                      v                      v             |  |
|  | TranslationEvent         AlertEvent            SpeakerEvents       |  |
|  |        │                      │                      │             |  |
|  | ┌──────┼───────────┐   ┌──────┼───────────┐   ┌──────┼───────────┐ |  |
|  | ▼      ▼           ▼   ▼      ▼           ▼   ▼      ▼           ▼ |  |
|  | UI  Summary     Database macOS  System    Database UI  Transcript  |  |
|  |     Engine    (AlertModel)Banner Sound  (SpeakerModel) Linker      |  |
|  +--------------------------------------------------------------------+  |
+------------------------------------+-------------------------------------+
                                     |
                                     v
+------------------------------------+-------------------------------------+
|                           INFRASTRUCTURE LAYER                           |
|       core/config.py  |  core/logger.py  |  core/exceptions.py        |
+--------------------------------------------------------------------------+
```

---

## Core Infrastructure Details

### 1. Configuration (`core/config.py`)
Driven by `pydantic-settings`. Environment settings are validated on initialization and cached using `@lru_cache` to eliminate disk I/O overhead.

### 2. Logging Subsystem (`core/logger.py`)
Powered by `loguru`. Standard library `logging` messages are intercepted via `InterceptHandler`. Supports colored console stdout and asynchronous rotating file logs (`data/logs/echomind.log`).

### 3. Error Handling (`core/exceptions.py`)
Custom exception hierarchy rooted at `EchoMindBaseException`. Specialized domain exceptions allow callers to handle domain failures precisely without catching generic exceptions.
