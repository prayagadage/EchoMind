"""Structured logging system built on Loguru.

Configures thread-safe console output and file rotation log sinks,
intercepts standard library logging messages, and enforces log level policies.
"""

import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from core.config import Settings


class InterceptHandler(logging.Handler):
    """Intercept standard library logging messages and route them to Loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        """Route standard log record to Loguru logger."""
        try:
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller frame to preserve stack trace accurate line numbers
        frame = sys._getframe(6)
        depth = 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back  # type: ignore[assignment]
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_logger(settings: "Settings") -> None:
    """Configure Loguru sinks based on application settings.

    Args:
        settings: Application Settings instance.
    """
    # Remove default Loguru handler
    logger.remove()

    # Ensure parent log directory exists
    log_file_path = Path(settings.log_file_path)
    log_file_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Console Log Sink
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )

    logger.add(
        sys.stdout,
        level=settings.log_level,
        format=log_format,
        colorize=True,
        backtrace=settings.debug,
        diagnose=settings.debug,
    )

    # 2. File Log Sink with Rotation & Retention
    logger.add(
        str(log_file_path),
        level=settings.log_level,
        format=log_format,
        serialize=settings.log_json_format,
        rotation=settings.log_rotation,
        retention=settings.log_retention,
        enqueue=True,  # Asynchronous thread-safe logging
        encoding="utf-8",
    )

    # 3. Intercept standard python logging (e.g. dependencies using standard logging)
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    logger.debug(
        f"Logging system initialized. Console & File Sink active. "
        f"Log file: {log_file_path}"
    )
