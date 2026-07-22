"""Command-line interface runner for EchoMind."""

import argparse
import sys

from app.container import ApplicationContainer
from loguru import logger


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments.

    Args:
        args: List of command line arguments or None for sys.argv[1:].

    Returns:
        argparse.Namespace: Parsed argument parameters.
    """
    parser = argparse.ArgumentParser(
        description="EchoMind: Offline AI Meeting Assistant for macOS Apple Silicon"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging and stack trace diagnostics",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Print version information and exit",
    )
    return parser.parse_args(args)


def run_cli(args: list[str] | None = None) -> int:
    """Run CLI runner sequence.

    Args:
        args: Command line parameters.

    Returns:
        int: Exit status code.
    """
    parsed = parse_args(args)

    if parsed.version:
        from core.constants import APP_NAME, VERSION

        logger.info(f"{APP_NAME} version {VERSION}")
        return 0

    container = ApplicationContainer()
    if parsed.debug:
        container.settings.debug = True
        container.settings.log_level = "DEBUG"

    container.initialize()
    logger.info("EchoMind CLI runner initialized successfully.")
    container.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(run_cli())
