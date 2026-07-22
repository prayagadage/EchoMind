"""Unit tests for Loguru logger setup."""

from core.config import Settings
from core.logger import setup_logger
from loguru import logger


def test_logger_file_creation(mock_settings: Settings) -> None:
    """Verify log file creation and writing upon initialization."""
    setup_logger(mock_settings)

    test_message = "Test diagnostic log entry for EchoMind"
    logger.info(test_message)

    log_path = mock_settings.log_file_path
    assert log_path.exists()

    content = log_path.read_text(encoding="utf-8")
    assert test_message in content
