"""Unit tests for UI CLI presentation runner."""

from ui.cli import run_cli


def test_cli_version_flag() -> None:
    """Verify --version flag executes cleanly."""
    status = run_cli(["--version"])
    assert status == 0


def test_cli_debug_flag() -> None:
    """Verify --debug flag initializes container cleanly."""
    status = run_cli(["--debug"])
    assert status == 0
