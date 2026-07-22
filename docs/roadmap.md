# EchoMind Development Roadmap

This document outlines the multi-phase technical roadmap for building EchoMind into a production-grade offline AI meeting assistant on macOS Apple Silicon.

---

## Phase 0: Software Foundation & Architecture Skeleton (CURRENT)
- [x] Design complete layered architecture.
- [x] Configure dependency management using `uv` and `pyproject.toml`.
- [x] Configure Ruff, Black, MyPy, and pytest tooling.
- [x] Build core infrastructure (`core/config.py`, `core/logger.py`, `core/exceptions.py`, `core/constants.py`).
- [x] Build application container (`app/container.py`) and runnable entry point (`app/main.py`).
- [x] Write architectural documentation, decisions ADR, and roadmap.

---

## Phase 1: Local Audio Capture Pipeline
- [ ] Implement macOS microphone stream listener (`modules/audio/mic.py`).
- [ ] Implement macOS system loopback audio capture (`modules/audio/loopback.py`).
- [ ] Build thread-safe audio ring buffer for chunking 16kHz mono audio streams.
- [ ] Write unit tests and stream verification benchmarks.

---

## Phase 2: Local Speech-to-Text (STT) Engine
- [ ] Integrate local Whisper model execution optimized for Apple Silicon (MPS / MLX).
- [ ] Benchmark transcription throughput on MacBook Air M2 (16 GB RAM).
- [ ] Build streaming transcription queue fed by Phase 1 audio chunks.
- [ ] Validate low-latency inference for English, Marathi, and Hindi audio streams.

---

## Phase 3: Multilingual Translation Engine
- [ ] Implement local neural translation pipeline for Marathi -> English and Hindi -> English.
- [ ] Implement language identification (LID) auto-switching.
- [ ] Build context-aware translation buffer to maintain sentence coherence across audio chunks.

---

## Phase 4: Real-Time Keyword Trigger & Alert Subsystem
- [ ] Implement high-performance phonetic and string matching engine for predefined keywords (e.g., `"Prayag"`).
- [ ] Build native macOS user notification dispatcher (`modules/keywords/notifier.py`).
- [ ] Implement sound cue and visual highlight triggers.

---

## Phase 5: Streaming & Final Meeting Summarization
- [ ] Integrate local quantized LLM runner (via MLX / llama.cpp) tuned for Apple Silicon memory footprint.
- [ ] Build live rolling window meeting context summarizer.
- [ ] Build structured post-meeting report generator (Action Items, Key Decisions, Agenda Summary).

---

## Phase 6: Native macOS Desktop GUI & Distribution
- [ ] Build responsive desktop UI (PyQt / PySide6 / native macOS wrapper).
- [ ] Implement menu bar quick-status integration and keyword alert panel.
- [ ] Create standalone macOS `.app` bundle and standalone installer package.
