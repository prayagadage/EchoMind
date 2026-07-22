# Changelog

All notable changes to the **EchoMind** project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
