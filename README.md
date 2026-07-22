# EchoMind

**EchoMind** is a production-grade, offline AI meeting assistant built specifically for macOS Apple Silicon (MacBook Air M2, 16 GB RAM). It continuously listens to meetings, transcribes and translates multilingual speech (Marathi, Hindi, English) into English, alerts the user when predefined keywords (such as `"Prayag"`) are spoken, and generates live and final meeting summaries—completely offline and locally on-device.

---

## Technical Stack & Architecture

- **Runtime Target**: Python `>= 3.11` on macOS Apple Silicon (`arm64`).
- **Package Management**: [`uv`](https://github.com/astral-sh/uv) fast Rust-based package installer and resolver.
- **Configuration**: Strongly-typed settings using `pydantic-settings` (Pydantic v2).
- **Logging**: Thread-safe structured logging with file rotation via `loguru`.
- **Quality Tools**: `ruff` (linter), `black` (formatter), `mypy` (strict type-checking), and `pytest` (test suite).

---

## Directory Structure

```
EchoMind/
├── app/                  # Application container and entry points
│   ├── container.py      # Dependency injection & lifecycle management
│   └── main.py           # Application entry point
├── core/                 # Core infrastructure
│   ├── config.py         # Pydantic Settings configuration
│   ├── constants.py      # System constants & platform specs
│   ├── exceptions.py     # Custom exception hierarchy
│   └── logger.py         # Loguru logger setup
├── modules/              # Domain modules
│   ├── audio/            # Audio capture stream (Phase 1)
│   ├── stt/              # Local Speech-to-Text (Phase 2)
│   ├── translation/      # Multilingual translation (Phase 3)
│   ├── keywords/         # Keyword alerts (Phase 4)
│   └── summary/          # Meeting summarization (Phase 5)
├── ui/                   # Presentation layer (CLI / GUI)
│   └── cli.py            # CLI entry runner
├── data/                 # Local data storage (logs, database, cache)
├── tests/                # Automated pytest suite
├── docs/                 # Documentation
│   ├── architecture.md   # Architectural design specification
│   ├── decisions.md      # Architecture Decision Records (ADRs)
│   └── roadmap.md        # Multi-phase project roadmap
├── assets/               # Static icons & UI resources
├── scripts/              # Environment helper scripts
├── pyproject.toml        # Unified project configuration & tool rules
├── README.md             # Project documentation
├── .gitignore            # Git exclusion rules
└── .env.example          # Environment settings template
```

---

## Quickstart Setup Guide

### 1. Prerequisites
Ensure you have Python 3.11+ and `uv` installed on your macOS machine:
```bash
brew install uv
```

### 2. Environment Setup
Clone the repository and execute the setup script:
```bash
chmod +x scripts/setup_env.sh
./scripts/setup_env.sh
```

Alternatively, configure manually:
```bash
uv sync --all-extras
cp .env.example .env
```

### 3. Launching the Application
Run the minimal application entry point:
```bash
uv run python -m app.main
```
You should see:
```text
2026-07-22 12:00:00.000 | INFO     | app.main:main:25 - EchoMind initialized successfully.
```

Or run via the CLI runner:
```bash
uv run python -m ui.cli --debug
```

---

## Running Quality Checks & Tests

Execute the automated test suite and static analysis tools:

```bash
# Run Pytest unit tests
uv run pytest

# Run Ruff linter
uv run ruff check .

# Run Black code formatter check
uv run black --check .

# Run MyPy type checker
uv run mypy app core modules ui
```

---

## Documentation Links

- [System Architecture](docs/architecture.md)
- [Architecture Decision Records (ADRs)](docs/decisions.md)
- [Project Development Roadmap](docs/roadmap.md)
