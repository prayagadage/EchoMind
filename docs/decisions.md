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

---

## ADR 10: Real-Time Intelligence Rule Engine & macOS Notification Service

- **Status**: Accepted
- **Context**: EchoMind requires real-time detection of configurable triggers ("Prayag", "प्रयाग", "Deadline", "Urgent", "Production") from transcript streams, desktop banner alerts, audio chimes, and persistent alert event recording without altering speech or translation pipelines.
- **Decision**: Implement `RuleEngine` with extensible `Rule` definitions, multilingual script-aware `KeywordMatcher`, `NotificationService` (macOS `osascript` banners + system sound chimes), and `AlertManager` worker publishing `AlertEvent`s and persisting `AlertModel` records via `AlertRepository`.
- **Rationale**: The `RuleEngine` provides an extensible abstraction supporting future rule types (Action Items, Deadlines, AI Semantic Detectors). Multilingual matching supports Devnagari and Latin script variants. Non-blocking `NotificationService` ensures desktop notifications and audio alert chimes never block continuous audio capture or speech recognition worker threads.
- **Consequences**: Native macOS notifications display banners via AppleScript, and `alerts` entries are recorded in SQLite.

---

## ADR 12: Speaker Identity Management, Foreign Key Indirection, and Safe Merging

- **Status**: Accepted
- **Context**: EchoMind requires transforming anonymous detected speakers (`Speaker A`, `Speaker B`) into user-manageable identities (custom display names, color coding, speaker statistics, timeline visualization, and speaker merging) without modifying original immutable transcript records or introducing biometric voice enrollment prematurely.
- **Decision**: Architect `SpeakerRegistry`, `SpeakerIdentityService`, `SpeakerMergeService`, `SpeakerStatisticsCalculator`, and `SpeakerUIAdapter` around **Foreign Key Indirection** (`transcripts.speaker_id -> speakers.id`).
- **Rationale**:
  1. **Foreign Key Indirection (`transcripts.speaker_id`)**: Storing `speaker_id` instead of hardcoding speaker name strings in `transcripts` guarantees that updating a speaker's `display_name` immediately updates every UI transcript view projection without mutating historical transcript text records.
  2. **Safe Speaker Merging**: Merging `Speaker C` into `Speaker A` performs an atomic foreign key update (`UPDATE transcripts SET speaker_id = dest_id WHERE speaker_id = target_id`), merges `last_seen` timestamps, deletes the target speaker record, and publishes `SpeakerMergedEvent`.
  3. **Preparation for Future Voice Recognition**: Storing persistent `speaker_id` foreign keys creates an ideal foundation for Phase 7 (Voice Profiles & Cross-Meeting Biometric Recognition). Future voice enrollment services can associate voice embeddings (`embedding_id`) directly to existing `speakers.id` entities without modifying transcript storage schemas.
- **Consequences**: Downstream UI components consume `SpeakerTranscriptProjection` objects, and speaker statistics/timelines are generated dynamically on demand.

---

## ADR 13: LLM Provider Abstraction & Meeting Intelligence Engine

- **Status**: Accepted
- **Context**: EchoMind requires structured intelligence extraction (action items, decisions, deadlines, questions, risks, follow-ups) from meeting transcripts using a local LLM. The system must remain offline-capable and backend-agnostic.
- **Decision**: Introduce a `core/llm/` package with a `LLMProvider` Protocol and `QwenMLXProvider` implementation using `mlx-lm` with `mlx-community/Qwen3-4B-4bit`. Implement `generate_json()` as a protocol-level utility that handles JSON extraction from markdown fences and Pydantic schema validation. Build `IntelligenceService` with dual-mode extraction: incremental (configurable window during live meetings) and final reconciliation (full-context re-extraction at meeting end). Deduplicate via `content_hash` unique constraints.
- **Rationale**:
  1. **Protocol-based DI**: Future providers (Ollama, OpenAI) implement the same `LLMProvider` protocol without touching intelligence code.
  2. **Structured extraction before summarization**: Discrete items preserve granular data that summaries would discard. Future summarization consumes extracted items as higher-quality inputs.
  3. **Incremental + final**: Real-time extraction gives users immediate visibility into action items during a meeting. Final reconciliation with full context merges duplicates and refines quality.
  4. **Content hash dedup**: SHA-256 hash on `(item_type, content)` prevents duplicate persistence across incremental and final passes.
- **Consequences**: `mlx-lm>=0.19.0` added as a dependency. `intelligence_items` table stores all extracted items with `is_final` flag distinguishing incremental from reconciled items.

---

## ADR 14: Prompt Engineering Layer & Meeting Summarization Engine

- **Status**: Accepted
- **Context**: EchoMind requires automated, offline meeting summarization generating Executive Summaries, Bullet Point Summaries, and Key Takeaways. To prevent hallucinations and ensure high summary density, prompt templates must be versioned cleanly and summaries anchored using pre-extracted structured meeting intelligence.
- **Decision**: Architect a dedicated Prompt Engineering Layer (`core/llm/prompts/` with submodules for `summarization`, `meeting_intelligence`, `translation`, and `qa`). Implement `SummaryBuilder` to aggregate meeting metadata, speaker display names, chronological transcripts, and pre-extracted Phase 7 structured intelligence (Action Items, Decisions, Deadlines, Questions, Risks) into ground-truth context bundles. Build `SummaryService` supporting live (incremental/periodic) and final (reconciliation) summary passes, stored in `meeting_summaries` SQLite table.
- **Rationale**:
  1. **Prompt Engineering Layer (`core/llm/prompts/`)**: Isolating prompt strings from Python business logic ensures prompt templates are testable, versioned, and easily tuneable without risking domain code side effects.
  2. **Ground-Truth Data Anchoring**: Feeding pre-extracted structured intelligence into the summary prompt ensures LLMs do not omit major commitments or hallucinate fake action items.
  3. **Structured JSON Output**: Validating response payloads via Pydantic `SummaryResponseSchema` guarantees robust structural separation of Executive Summary, Bullet Points, and Key Takeaways.
- **Consequences**: Summary records are stored in `meeting_summaries` table with model version tracking. `summary_service` is accessible via `ApplicationContainer`.

---

## ADR 15: Vector Store Abstraction & Local Semantic Search Engine

- **Status**: Accepted
- **Context**: EchoMind requires an offline local semantic search and knowledge base across meeting transcripts, summaries, and Phase 7 structured intelligence (Action Items, Decisions, Risks, Questions, Deadlines). To keep search independent of underlying database implementations and allow future experimentation, vector storage must be abstracted behind a provider interface.
- **Decision**: Introduce a `core/vector/` package with `VectorStore` Protocol (`base.py`) and `SQLiteVectorStore` provider (`sqlite_provider.py`) using SQLite storage and NumPy dot-product Cosine Similarity. Implement `EmbeddingService` in `modules/search/embedding_service.py` with `LocalSemanticEmbeddingProvider` generating 384-dimensional normalized $L_2$ vectors. Build `KnowledgeIndexer` and `SearchService` supporting incremental indexing with content hash deduplication, top-k similarity ranking, meeting filters, and metadata enrichment (meeting titles, speaker display names, timestamps).
- **Rationale**:
  1. **Vector Store Interface**: Abstracting vector storage behind `VectorStore` Protocol prevents vendor/driver lock-in and allows swapping SQLite for alternative vector backends in the future without changing search logic.
  2. **Dedicated Local Embedding Model**: Generative decoders (Qwen 3 4B) are unsuitable for batch vector embedding generation. A 384-dim normalized embedding generator provides fast (<5ms per batch) and zero-network vector representations.
  3. **Multilingual Translation Integration**: Transcripts in Marathi and Hindi use their translated English text for embedding vector generation, enabling cross-lingual semantic discovery in natural English queries.
- **Consequences**: `vector_embeddings` table and SQLite vector store maintain indexed vectors. `search_service` and `indexer` are wired via `ApplicationContainer`.

---

## ADR 16: AI Meeting Assistant & Conversational RAG Engine

- **Status**: Accepted
- **Context**: EchoMind requires an AI Meeting Assistant capable of answering natural-language questions about past meetings using Retrieval-Augmented Generation (RAG). Answers must be strictly grounded in underlying meeting records, support multi-turn conversation memory, and provide source citations without LLM hallucination.
- **Decision**: Architect the `modules/assistant/` package with `QueryParser`, `RetrievalService` (wrapping Phase 9 `SearchService`), `ContextBuilder` (formatting `[Ref N]` context blocks), `AssistantPromptBuilder` (integrating system prompt from `core/llm/prompts/qa.py`), `ConversationMemory` (maintaining multi-turn dialogue history), `ResponseGenerator` (parsing answers and mapping `[Ref N]` tags to `Citation` objects), and `AssistantService` orchestrator.
- **Rationale**:
  1. **Strict RAG Grounding**: Querying `SearchService` for semantic vector hits *before* LLM synthesis transforms speculative text generation into grounded context reading, preventing hallucinations.
  2. **Multi-Turn Dialogue Memory**: `ConversationMemory` maintains a thread-safe sliding window buffer per session ID, permitting follow-up questions to retain context across conversation turns.
  3. **Source Attribution & Citations**: `ContextBuilder` tags every retrieved snippet with reference markers (`[Ref 1]`, `[Ref 2]`), allowing `ResponseGenerator` to map claims back to structured `Citation` objects (meeting title, speaker display name, timestamp, entity type).
  4. **Anti-Hallucination Fallback**: If vector retrieval returns zero hits (or hits below confidence threshold), `AssistantService` immediately returns a factual fallback response without making an ungrounded LLM call.
- **Consequences**: `assistant_service` is accessible via `ApplicationContainer`. Conversational turn memory is maintained in-memory per session.

---

## ADR 17: Desktop User Experience (Desktop UI & macOS Integration)

- **Status**: Accepted
- **Context**: EchoMind requires a polished macOS application interface to expose real-time audio capture, streaming speech recognition, transcript management, meeting summaries, RAG AI Chat, global search, preferences, document exports, and system tray integration.
- **Decision**: Adopt MVVM (Model-View-ViewModel) architecture using PyQt6 for desktop UI components. Implement ViewModels (`DashboardVM`, `LibraryVM`, `TranscriptVM`, `SummaryVM`, `ChatVM`, `SearchVM`, `SettingsVM`, `ExportVM`) inheriting from `QObject` with reactive signals/slots. Implement `ExportService` for multi-format document generation (`.md`, `.json`, `.pdf`, `.docx`), `SettingsService` for persisting user preferences to disk, `MenuBarTrayApp` for native macOS menu bar status, and `NativeNotificationManager` for system alerts.
- **Rationale**:
  1. **Strict MVVM Separation**: Views interact only with ViewModels via Qt Signals/Slots, and ViewModels interact with underlying backend services. Views never query SQLite databases or execute AI models directly.
  2. **Asynchronous Execution**: Heavy background tasks (LLM summarization, RAG Q&A generation, vector search, document export) run asynchronously on background worker threads, keeping the GUI thread responsive at 60 FPS.
  3. **Native macOS HIG Aesthetics**: Theme styling tokens in `ui/desktop/theme.py` adhere to macOS Human Interface Guidelines, supporting both Dark and Light visual themes.
  4. **Multi-Format Export**: `ExportService` gathers complete meeting model graphs from repositories and renders formatted Markdown, JSON, PDF (via ReportLab), and DOCX (via python-docx) reports.
- **Consequences**: `settings_service` and `export_service` are accessible via `ApplicationContainer`. `MainWindow` shell renders all tabs and tray integration.




