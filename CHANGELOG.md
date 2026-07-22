# Changelog

All notable changes to the **EchoMind** project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
