"""Command-line interface runner for EchoMind."""

import argparse
import sys

from app.container import ApplicationContainer
from loguru import logger
from modules.stt.transcript_event import TranscriptEvent
from modules.stt.transcript_formatter import TranscriptFormatter


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
    parser.add_argument(
        "--stt",
        action="store_true",
        help="Run real-time streaming speech recognition listener",
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

    if parsed.stt:
        from modules.audio.engine import AudioEngine
        from modules.stt.transcription_pipeline import TranscriptionPipeline

        logger.info("Starting EchoMind Real-Time Speech Recognition...")

        event_bus = container.event_bus if hasattr(container, "event_bus") else None
        audio_engine = AudioEngine(settings=container.settings, event_bus=event_bus)
        pipeline = TranscriptionPipeline(event_bus=audio_engine.event_bus)

        def cli_transcript_listener(event: TranscriptEvent) -> None:
            output = TranscriptFormatter.format_console(event)
            logger.info(f"TRANSCRIPT >> {output}")

        audio_engine.event_bus.subscribe(TranscriptEvent, cli_transcript_listener)

        pipeline.start()
        audio_engine.start()

        logger.info("Listening... Press Ctrl+C to stop.")
        try:
            import time

            while True:
                time.sleep(1.0)
        except KeyboardInterrupt:
            logger.info("Stopping speech recognition runner...")
            audio_engine.stop()
            pipeline.stop()

    container.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(run_cli())
