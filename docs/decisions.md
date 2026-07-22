# EchoMind Architecture Decision Records (ADRs)

This document records key architectural and technology choices made for the EchoMind project, explaining the context, decision, and consequences for each choice.

---

## ADR 1: Python 3.11+ as Target Runtime

- **Status**: Accepted
- **Context**: EchoMind requires high-performance processing on Apple Silicon, modern type safety, and integration with PyTorch/MLX ecosystems.
- **Decision**: Target Python `>= 3.11`.
- **Rationale**: Python 3.11 introduces major CPython performance improvements (10–60% speedup), modern type union syntaxes (`X | Y`), native task groups in asyncio, and optimal Apple Silicon wheel availability.
- **Consequences**: Support for legacy Python versions (< 3.11) is explicitly omitted.

---

## ADR 2: Dependency Management via `uv`

- **Status**: Accepted
- **Context**: Managing Python dependencies across virtual environments can be slow and brittle using standard `pip` or heavy tools like `poetry`.
- **Decision**: Adopt `uv` as the official project dependency manager and virtualenv orchestrator.
- **Rationale**: `uv` is written in Rust and operates 10–100x faster than standard Python package managers. It supports standard `pyproject.toml` configuration and lockfile workflows seamlessly.
- **Consequences**: Developers need `uv` installed (`brew install uv`).

---

## ADR 3: Configuration Management via `pydantic-settings`

- **Status**: Accepted
- **Context**: Hardcoded values or raw `os.getenv()` calls introduce runtime bugs, missing validation, and type coercion issues.
- **Decision**: Use `pydantic-settings` (Pydantic v2) for strongly-typed configuration models.
- **Rationale**: Guarantees type checking at application bootstrap, provides automatic `.env` environment overrides, auto-documents settings parameters, and avoids mutable global variables.
- **Consequences**: Settings changes require updating `core/config.py` models.

---

## ADR 4: Logging Architecture via `loguru`

- **Status**: Accepted
- **Context**: Built-in `logging` module requires verbose boilerplate setup, lacks modern structured formatting out-of-the-box, and makes thread-safe file rotation tedious.
- **Decision**: Standardize on `loguru` with an intercept handler for standard `logging`.
- **Rationale**: `loguru` provides asynchronous file rotation/retention, rich colored terminal output, stack trace backtraces, and zero-boilerplate logging statements throughout the codebase.
- **Consequences**: Standard logging library calls are intercepted automatically.

---

## ADR 5: Layered Architecture for 50,000+ LOC Scale

- **Status**: Accepted
- **Context**: As the project scales across audio pipelines, ML models, translation, and UI layers, monolithic or unstructured code bases quickly degrade in maintainability.
- **Decision**: Organize into `core/`, `modules/`, `app/`, and `ui/` top-level layers following Dependency Inversion Principles.
- **Rationale**: High cohesion and low coupling ensure domain modules can be tested in isolation and ML engines upgraded without breaking presentation or infrastructure code.
- **Consequences**: Code must strictly respect layer boundaries (`core` cannot import from `app` or `modules`).

---

## ADR 6: Local Audio Capture via `sounddevice` and In-Memory Ring Buffer

- **Status**: Accepted
- **Context**: EchoMind requires continuous, low-latency microphone audio streaming without saving audio recordings to WAV or writing audio files to disk (privacy and disk I/O constraints).
- **Decision**: Use `sounddevice` for PortAudio C-level callbacks, pre-allocated NumPy `float32` circular ring buffers (`AudioBuffer`), and a decoupled `EventBus`.
- **Rationale**: CoreAudio integration via `sounddevice` delivers frame latency below 10 ms. In-memory pre-allocated NumPy arrays eliminate garbage collection pauses and file system persistence. The `EventBus` ensures downstream ML models (Whisper, Keyword Scanner) subscribe asynchronously without coupling to the audio engine.
- **Consequences**: Microphone audio must be accessed via subscriber events or ring buffer slices; no disk WAV files exist.

---

## ADR 7: Local Multilingual STT via `mlx-whisper` and Silero VAD

- **Status**: Accepted
- **Context**: Real-time speech-to-text on Apple Silicon must run strictly offline, support multilingual conversations (Marathi, Hindi, English), filter out background silence, and leverage hardware acceleration (Metal / Neural Engine).
- **Decision**: Integrate `mlx-whisper` for local inference and `VoiceActivityDetector` (Silero VAD thresholds) for active speech segmentation.
- **Rationale**: `mlx-whisper` is native to Apple Silicon MLX framework, utilizing Metal and ANE for low-power, high-throughput inference. Voice Activity Detection filters silent chunks before invoking Whisper, conserving battery and GPU compute. Decoupled `TranscriptEvent`s are published onto the `EventBus` for presentation and future Phase 3 translation subscribers.
- **Consequences**: Whisper models run on local GPU/ANE; no cloud API calls or external service calls are made.

---

## ADR 8: Persistent Storage via SQLAlchemy 2.0 ORM, SQLite, and Repository Pattern

- **Status**: Accepted
- **Context**: EchoMind requires a robust, local persistent memory system to record meeting sessions and transcript segments, support full-text keyword searches, and allow decoupled auto-persistence without speech code directly coupling to database drivers.
- **Decision**: Adopt SQLAlchemy 2.0 ORM with SQLite (`data/db/echomind.db`), Repository Pattern (`MeetingRepository`, `TranscriptRepository`), and `TranscriptService` EventBus auto-persistence.
- **Rationale**: SQLAlchemy 2.0 provides type-safe ORM mappings and session management. SQLite WAL mode ensures fast local reads and writes. The Repository Pattern encapsulates SQL queries, while `TranscriptService` subscribes to `TranscriptEvent` on the `EventBus`, keeping STT modules 100% database-agnostic. Schema columns for translation, speaker diarization, and embeddings are pre-designed for future phases.
- **Consequences**: Local SQLite file is maintained at `data/db/echomind.db`.

---

## ADR 9: Independent Worker Architecture & Term-Preserving Translation

- **Status**: Accepted
- **Context**: EchoMind requires automatic, offline translation of Marathi (`mr`) and Hindi (`hi`) transcripts into English while leaving original transcripts untouched, preserving technical terms ("Python", "SQL", "API", "Prayag", "EchoMind"), and adhering to an decoupled independent event worker design.
- **Decision**: Architect `TranslationService` as an independent worker consuming `TranscriptEvent`s, translating via `TranslationEngine`, publishing `TranslationEvent` payloads, and storing translations in a separate `TranslationModel` table via `TranslationRepository`.
- **Rationale**: Decoupling workers around events enables parallel processing (Translation, Keyword Detection, Diarization) without tight coupling or sequential pipelines. Technical term preservation prevents corruption of code terms and proper names. Storing translations in a dedicated `translations` table guarantees original transcript immutability.
- **Consequences**: Downstream UI and Summary subscribers consume `TranslationEvent` payloads asynchronously over the `EventBus`.
