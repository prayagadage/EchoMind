"""Pytest configuration and shared fixtures for EchoMind test suite."""

import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest
from core.config import Settings


@pytest.fixture
def temp_log_dir() -> Generator[Path, None, None]:
    """Provide temporary directory path for log testing isolation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_settings(temp_log_dir: Path) -> Settings:
    """Provide isolated Settings instance pointing to temporary log path."""
    return Settings(
        app_name="EchoMindTest",
        app_env="testing",
        debug=True,
        log_level="DEBUG",
        log_file_path=temp_log_dir / "test_echomind.log",
    )
