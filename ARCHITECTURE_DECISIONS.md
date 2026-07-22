# EchoMind Architecture Decision Records (ADRs)

> Detailed decision records are maintained in [docs/decisions.md](docs/decisions.md).

This document captures the key architectural decisions and technology selections made for **EchoMind**, serving as an immutable log of design trade-offs.

---

## Index of ADRs

### [ADR-001: Python 3.11+ as Target Runtime](docs/decisions.md#adr-1-python-311-as-target-runtime)
- **Choice**: Python `>= 3.11`
- **Why**: 10–60% speedup in CPython runtime, modern type union syntax (`X | Y`), and native compatibility with PyTorch and Apple Silicon MLX bindings.

### [ADR-002: Dependency & Virtualenv Management via `uv`](docs/decisions.md#adr-2-dependency-management-via-uv)
- **Choice**: `uv` + `pyproject.toml`
- **Why**: 10–100x faster dependency resolution and virtualenv creation than `pip` or `poetry`.

### [ADR-003: Configuration Management via `pydantic-settings`](docs/decisions.md#adr-3-configuration-management-via-pydantic-settings)
- **Choice**: Pydantic v2 `BaseSettings`
- **Why**: Strongly-typed environment validation at startup, automatic `.env` loading, and elimination of mutable global state.

### [ADR-004: Logging Architecture via `loguru`](docs/decisions.md#adr-4-logging-architecture-via-loguru)
- **Choice**: `loguru` with standard logging interception
- **Why**: Zero-boilerplate thread-safe logging, colorized stdout, automatic file log rotation/retention, and stack trace backtrace diagnostics.

### [ADR-005: Layered Architecture for 50,000+ LOC Scale](docs/decisions.md#adr-5-layered-architecture-for-50000-loc-scale)
- **Choice**: 4-Layer Separation (`core/`, `modules/`, `app/`, `ui/`)
- **Why**: Strict separation of concerns (SOLID), high cohesion, low coupling, and zero circular dependencies.

### [ADR-006: Local Audio Capture via `sounddevice` and In-Memory Ring Buffer](docs/decisions.md#adr-6-local-audio-capture-via-sounddevice-and-in-memory-ring-buffer)
- **Choice**: `sounddevice` + NumPy Ring Buffer + `EventBus`
- **Why**: Low-latency CoreAudio callbacks (<10 ms), zero WAV disk writes, and decoupled subscriber streaming for future ML modules.

### [ADR-007: Local Multilingual STT via `mlx-whisper` and Silero VAD](docs/decisions.md#adr-7-local-multilingual-stt-via-mlx-whisper-and-silero-vad)
- **Choice**: `mlx-whisper` + `VoiceActivityDetector` + `TranscriptEvent`
- **Why**: Apple Silicon Metal/ANE hardware acceleration, automatic Marathi/Hindi/English detection, silence filtering, and decoupled event streaming.

### [ADR-008: Persistent Storage via SQLAlchemy 2.0 ORM, SQLite, and Repository Pattern](docs/decisions.md#adr-8-persistent-storage-via-sqlalchemy-20-orm-sqlite-and-repository-pattern)
- **Choice**: SQLAlchemy 2.0 + SQLite + Repository Pattern + EventBus Auto-Persistence
- **Why**: Type-safe ORM entities, decoupled event-driven storage, full-text keyword search, and pre-designed schema extension columns.

### [ADR-009: Independent Worker Architecture & Term-Preserving Translation](docs/decisions.md#adr-9-independent-worker-architecture--term-preserving-translation)
- **Choice**: `TranslationService` Worker + `TranslationEvent` + Technical Term Guard + `TranslationRepository`
- **Why**: Fan-out event architecture, non-destructive original transcript storage, term preservation, and support for future target languages.

### [ADR-010: Real-Time Intelligence Rule Engine & macOS Notification Service](docs/decisions.md#adr-10-real-time-intelligence-rule-engine--macos-notification-service)
- **Choice**: `RuleEngine` + `NotificationService` (macOS UserNotifications)
- **Why**: Real-time business logic execution, low-latency UI feedback, and native OS-level interaction for critical alerts.

### [ADR-011: Online Acoustic Feature Streaming Diarization for Apple Silicon](docs/decisions.md#adr-11-online-acoustic-feature-streaming-diarization-for-apple-silicon)
- **Choice**: `SpeakerSegmenter` Acoustic Feature Vector Clustering + `SpeakerService` Event Worker
- **Why**: Ultra-low memory (<15MB) and CPU (<3%) footprint on M2 Air without GPU contention, sub-50ms processing latency, and intra-meeting speaker continuity tracking.

---

For full details, context, and consequences for each ADR, refer to [docs/decisions.md](docs/decisions.md).
