# Changelog

All notable changes to the **EchoMind** project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.8.0] - 2026-07-22 (Phase 8: Meeting Summarization Engine)

### Added
- `core/llm/prompts/` — Dedicated Prompt Engineering Layer (`summarization`, `meeting_intelligence`, `translation`, `qa`)
- `modules/summary/` — Meeting Summarization Engine package
- `SummaryBuilder` aggregating meeting metadata, speakers, transcripts, and Phase 7 structured intelligence
- `SummaryService` supporting live (incremental) and final summary generation workflows as well as summary regeneration
- `MeetingSummaryModel` ORM entity storing Executive Summary, Bullet Points, and Key Takeaways
- `SummaryResponseSchema` Pydantic model for output validation
- `SummaryRepository` for database CRUD, version updates, and non-final cleanup
- `SummaryGeneratedEvent` published on EventBus
- 10 new unit and integration tests in `tests/test_summary.py`
- Executable demonstration script `scripts/demo_summary.py`
- ADR-014: Prompt Engineering Layer & Meeting Summarization Engine

### Changed
- `app/container.py` — Exposed `summary_service` wired with `QwenMLXProvider`
- `modules/meeting_intelligence/prompt_builder.py` — Refactored to import from `core.llm.prompts.meeting_intelligence`

---

## [0.7.0] - 2026-07-22 (Phase 7: Meeting Intelligence Engine)

### Added
- `core/llm/` — LLM provider abstraction (`LLMProvider` Protocol + `generate_json()` utility)
- `core/llm/mlx_provider.py` — `QwenMLXProvider` using `mlx-community/Qwen3-4B-4bit` via `mlx-lm`
- `modules/meeting_intelligence/` — Full intelligence extraction module
- `IntelligenceService` with dual-mode: incremental (live meeting) + final reconciliation
- `PromptBuilder` assembling timestamped speaker-attributed transcript context
- `ResponseParser` with Pydantic JSON validation and markdown fence extraction
- `IntelligenceRepository` with content hash deduplication
- `IntelligenceItemModel` ORM (action items, decisions, deadlines, questions, risks, follow-ups)
- `IntelligenceExtractedEvent` published on EventBus after extraction
- 25 new tests covering parser, repository, service pipeline, dedup, and edge cases
- `scripts/demo_meeting_intelligence.py` end-to-end demonstration
- ADR-013: LLM Provider Abstraction & Meeting Intelligence Engine

### Changed
- `pyproject.toml` — Added `mlx-lm>=0.19.0` dependency
- `app/container.py` — Wired `intelligence_service` with `QwenMLXProvider` DI
- `core/exceptions.py` — Added `IntelligenceError`

---

## [0.6.2] - 2026-07-22 (Phase 6B: Speaker Identity Management System)

### Added
- **Speaker Registry (`modules/speaker/speaker_registry.py`)**: `SpeakerRegistry` managing speaker entity creation, palette color assignment (`#4F46E5`, `#10B981`, `#F59E0B`, etc.), and lookups.
- **Speaker Identity Service (`modules/speaker/speaker_identity_service.py`)**: `SpeakerIdentityService` handling user speaker renames (`Speaker A` -> `Rahul`), hex color code assignments, and publishing `SpeakerUpdatedEvent`.
- **Speaker Merge Service (`modules/speaker/speaker_merge_service.py`)**: `SpeakerMergeService` executing atomic speaker merges (`Speaker C` -> `Rahul`), reassigning `TranscriptModel.speaker_id` foreign keys in SQLite, updating `last_seen`, and publishing `SpeakerMergedEvent`.
- **Speaker Statistics & Timeline (`modules/speaker/speaker_statistics.py`)**: `SpeakerStatisticsCalculator` computing speaking time, turn count, average/longest turn duration, and generating `SpeakerTimelineSegment` models for UI visualization.
- **Speaker UI Adapter (`modules/speaker/ui_adapter.py`)**: `SpeakerUIAdapter` projecting transcript records with dynamic speaker identity metadata (`effective_speaker_name`, `speaker_color`) without mutating historical transcript text records.
- **Database Schema Extensions (`modules/storage/models.py` & `repositories.py`)**: Added `display_name` and `color` columns to `SpeakerModel` table and added `rename`, `update_color`, `delete`, and `reassign_transcripts` methods to `SpeakerRepository`.
- **Unit Tests & Demo (`tests/test_speaker_identity.py` & `scripts/demo_speaker_identity.py`)**: Comprehensive test suite and interactive demonstration script.

## [0.6.1] - 2026-07-22 (Phase 6A: Streaming Speaker Segmentation System)

### Added
- **SpeakerSegmenter Engine (`modules/speaker/speaker_segmenter.py`)**: Real-time acoustic spectral feature vector extraction and online centroid clustering engine detecting speaker boundaries and tracking intra-meeting speaker continuity.
- **SpeakerService Event Worker (`modules/speaker/speaker_service.py`)**: Independent worker subscribing to `AudioChunk` and `TranscriptEvent`, managing temporary speaker labels (`Speaker A`, `Speaker B`), linking `TranscriptModel.speaker_id` in SQLite, and publishing `SpeakerEvents`.
- **Speaker Events Dataclasses (`modules/speaker/speaker_events.py`)**: `SpeakerStartedEvent`, `SpeakerEndedEvent`, `SpeakerChangedEvent`, and `SpeakerAssignedEvent` payloads.
- **Speaker Database Persistence (`modules/storage/models.py` & `repositories.py`)**: `SpeakerModel` ORM entity (`speakers` table) and `SpeakerRepository` for SQLite persistence.
- **Unit Tests & Demo (`tests/test_speaker.py` & `scripts/demo_speaker.py`)**: Comprehensive unit test suite and live interactive demonstration script.

## [0.6.0] - 2026-07-22 (Phase 5: Real-Time Intelligence & Alert System)

### Added
- **Multilingual KeywordMatcher (`modules/intelligence/keyword_matcher.py`)**: Script-aware keyword and pattern matcher supporting "Prayag", "प्रायग", "प्रयाग", "Deadline", "Urgent", and "Production".
- **Extensible RuleEngine (`modules/intelligence/rule_engine.py`)**: Rule engine evaluating incoming transcripts against configurable `Rule` objects with severities (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
- **macOS NotificationService (`modules/intelligence/notification_service.py`)**: Native desktop notification banners via `osascript` and system alert sound chimes (`afplay` / `Glass.aiff`).
- **AlertManager Event Worker (`modules/intelligence/alert_manager.py`)**: Independent worker subscribing to `TranscriptEvent` and `TranslationEvent`, publishing `AlertEvent`, and orchestrating notifications + DB persistence.
- **Alert Persistence (`modules/storage/models.py` & `repositories.py`)**: `AlertModel` ORM entity and `AlertRepository` for SQLite alert history persistence.
- **Unit Tests & Demo (`tests/test_intelligence.py` & `scripts/demo_alerts.py`)**: Comprehensive test suite and live interactive demonstration script.

## [0.5.0] - 2026-07-22 (Phase 4: Local Translation Engine & Independent Event Worker System)

### Added
- **Independent Translation Worker**: Built `TranslationService` (`modules/translation/service.py`) listening to `TranscriptEvent`s on `EventBus`, translating Marathi and Hindi into English, emitting `TranslationEvent`s, and storing translations in SQLite.
- **Translation Event Payload**: Created immutable `TranslationEvent` data model (`modules/translation/translation_event.py`) for decoupled downstream UI and summary subscribers.
- **Neural Translation & Term Guard**: Implemented `TranslationEngine` (`modules/translation/engine.py`) for local translation with automatic preservation of technical terms, code snippets, APIs, model names, and author names ("Prayag", "EchoMind", "Python", "SQL").
- **Database Schema & Repository**: Added `TranslationModel` ORM entity (`modules/storage/models.py`) and `TranslationRepository` (`modules/storage/repositories.py`) for separate, non-destructive translation persistence.
- **Application Container Wiring**: Updated `ApplicationContainer` (`app/container.py`) to expose `translation_service`.
- **Demonstration & Test Suite**: Added `scripts/demo_translation.py` and comprehensive unit test suite (`tests/test_translation.py`).

---

## [0.4.0] - 2026-07-22 (Phase 3: Persistent Memory & Storage System)

### Added
- **SQLAlchemy 2.0 ORM Mappings**: Implemented `MeetingModel` and `TranscriptModel` (`modules/storage/models.py`) with pre-designed schema extension columns (`translated_text`, `speaker_label`, `embedding_id`).
- **Database Engine**: Created `DatabaseEngine` (`modules/storage/db.py`) managing SQLite connections (`data/db/echomind.db`), WAL mode, session scoping, and automatic table creation.
- **Repository Pattern**: Implemented `MeetingRepository` and `TranscriptRepository` (`modules/storage/repositories.py`) for decoupled CRUD and keyword search operations.
- **Transcript Service**: Built `TranscriptService` (`modules/storage/service.py`) managing meeting lifecycles (`start_meeting`, `end_meeting`), retrieving meeting histories, and subscribing to `TranscriptEvent` on `EventBus` for auto-persistence.
- **Application Container Wiring**: Updated `ApplicationContainer` (`app/container.py`) to manage `DatabaseEngine` and `TranscriptService` lifespans.
- **Demonstration & Tests**: Created `scripts/demo_storage.py` and comprehensive unit test suite (`tests/test_storage.py`).

---

## [0.3.0] - 2026-07-22 (Phase 2: Real-Time Multilingual Speech Recognition)

### Added
- **MLX Whisper Engine**: Implemented `MLXWhisperEngine` (`modules/stt/whisper_engine.py`) leveraging Apple Silicon Metal/ANE hardware acceleration for offline STT and automatic language detection (Marathi, Hindi, English).
- **Silence & Speech Filtering**: Implemented `VoiceActivityDetector` (`modules/stt/vad.py`) evaluating energy and VAD thresholds to filter out silent pauses and ambient noise.
- **Transcript Event Model**: Created immutable `TranscriptEvent` data model (`modules/stt/transcript_event.py`) encapsulating text, language codes (`mr`, `hi`, `en`), timestamps, confidence scores, and sequence numbers.
- **Streaming STT Pipeline**: Implemented `TranscriptionPipeline` (`modules/stt/transcription_pipeline.py`) subscribing to `AudioChunk` events from Phase 1 `EventBus`, accumulating active speech frames, running Whisper STT, and publishing `TranscriptEvent` payloads.
- **Transcript Formatter**: Built `TranscriptFormatter` (`modules/stt/transcript_formatter.py`) for clean console timestamping, language tag colorization, and JSON rendering.
- **CLI Live STT Flag**: Updated `ui/cli.py` to support `--stt` CLI flag for live interactive speech recognition.
- **Demonstration & Test Suite**: Added `scripts/demo_stt.py` and comprehensive unit test suite (`tests/test_stt.py`).

---

## [0.2.0] - 2026-07-22 (Phase 1: Local Audio Capture Engine)

### Added
- **Event Bus Engine**: Implemented generic, thread-safe `EventBus` (`core/event_bus.py`) supporting asynchronous Publish/Subscribe decoupling of audio producers and ML consumers.
- **Audio Models**: Added `AudioChunk` (encapsulated NumPy float32 array, timestamp, sample rate, channels, RMS calculation) and `AudioDeviceInfo` dataclasses (`modules/audio/models.py`).
- **In-Memory Ring Buffer**: Implemented pre-allocated `AudioBuffer` circular ring buffer (`modules/audio/buffer.py`) storing configurable recent $N$ seconds of audio in memory without disk persistence.
- **Hardware Device Manager**: Implemented `AudioDeviceManager` (`modules/audio/device.py`) for CoreAudio microphone discovery, device selection, and error handling.
- **Audio Engine State Machine**: Implemented `AudioEngine` (`modules/audio/engine.py`) for continuous `sounddevice` microphone capture with `START`, `PAUSE`, `RESUME`, and `STOP` states.
- **Demonstration Script**: Created `scripts/demo_audio.py` for live interactive testing of audio streaming, RMS level visualization, and pause/resume transitions.
- **Unit Tests**: Added comprehensive test suite (`tests/test_audio.py`) verifying buffer wrap-around, event bus dispatching, device queries, and state machine controls.

---

## [0.1.0] - 2026-07-22 (Phase 0: Software Foundation Skeleton)

### Added
- **Project Structure**: Established modular 4-layer layout (`core/`, `modules/`, `app/`, `ui/`, `data/`, `tests/`, `docs/`, `assets/`, `scripts/`).
- **Package Management**: Configured `uv` package synchronization and build parameters in `pyproject.toml`.
- **Quality & Static Tooling**: Integrated `ruff` (linter), `black` (formatter), `mypy` (strict type-checking), and `pytest` (test suite with coverage).
- **Configuration Subsystem**: Implemented strongly-typed `Settings` using `pydantic-settings` with `.env` file loading, validation, and LRU caching (`core/config.py`).
- **Logging Architecture**: Implemented thread-safe `Loguru` configuration with colored terminal output, rotating file logs (`data/logs/echomind.log`), and standard logging interception (`core/logger.py`).
- **Error Handling**: Built custom exception hierarchy rooted at `EchoMindBaseException` (`core/exceptions.py`).
- **System Constants**: Defined system defaults and Apple Silicon macOS platform specifications (`core/constants.py`).
- **Application Lifespan & Entry Point**: Built `ApplicationContainer` (`app/container.py`), `ui/cli.py` presentation runner, and main execution entry point (`app/main.py`) printing `"EchoMind initialized successfully."`.
- **Documentation**:
  - `README.md`: Quickstart instructions, execution commands, and project summary.
  - `docs/architecture.md`: Comprehensive system architecture and layer specifications.
  - `docs/decisions.md`: Architecture Decision Records (ADRs) detailing technology choices.
  - `docs/roadmap.md`: Multi-phase project roadmap.
  - `ARCHITECTURE_DECISIONS.md`: Direct link & reference to ADRs.
- **Environment & Scripts**: Created `.gitignore`, `.env.example`, and `scripts/setup_env.sh`.
- **Automated Tests**: Unit test suite covering configuration, logger, container lifespan, and CLI flags (`tests/`).
