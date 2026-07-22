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
