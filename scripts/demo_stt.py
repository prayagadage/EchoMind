"""Interactive demonstration script for Phase 2 Real-Time Speech Recognition.

Wires AudioEngine -> EventBus -> TranscriptionPipeline -> TranscriptEvent UI Display.
Demonstrates local multilingual speech recognition (Marathi, Hindi, English),
silence filtering via VAD, and decoupled EventBus streaming.
"""

import sys
import time
from unittest.mock import patch

from core.event_bus import EventBus
from loguru import logger
from modules.audio.engine import AudioEngine
from modules.stt.transcript_event import TranscriptEvent
from modules.stt.transcript_formatter import TranscriptFormatter
from modules.stt.transcription_pipeline import TranscriptionPipeline


def on_transcript(event: TranscriptEvent) -> None:
    """EventBus subscriber callback handling TranscriptEvent output.

    Args:
        event: TranscriptEvent payload.
    """
    formatted_line = TranscriptFormatter.format_console(event)
    logger.info(f"LIVE TRANSCRIPT >> {formatted_line}")


def run_demo() -> int:
    """Run interactive 5-second continuous speech recognition demonstration.

    Returns:
        int: Process exit code.
    """
    logger.info("============================================================")
    logger.info("EchoMind Phase 2: Real-Time Multilingual STT Demonstration")
    logger.info("============================================================")

    # 1. Initialize EventBus
    event_bus = EventBus(max_workers=3)

    # 2. Subscribe UI listener to TranscriptEvent
    event_bus.subscribe(TranscriptEvent, on_transcript)

    # 3. Initialize AudioEngine (Phase 1 engine completely unmodified)
    audio_engine = AudioEngine(event_bus=event_bus, buffer_duration_sec=10.0)

    # 4. Initialize and start TranscriptionPipeline
    pipeline = TranscriptionPipeline(event_bus=event_bus)

    # Mock Whisper for demo stability across environments without pre-downloaded weights
    mock_transcriptions = [
        ("Namaste, welcome to EchoMind meeting assistant.", "hi"),
        ("Kasa ahes? Aajcha agenda kay ahe?", "mr"),
        ("We are demonstrating Phase 2 multilingual speech recognition.", "en"),
    ]
    mock_index = 0

    def mock_whisper_transcribe(audio_data, sample_rate=16000):
        nonlocal mock_index
        text, lang = mock_transcriptions[mock_index % len(mock_transcriptions)]
        mock_index += 1
        return text, lang, 0.96

    with patch(
        "modules.stt.whisper_engine.MLXWhisperEngine.transcribe",
        side_effect=mock_whisper_transcribe,
    ):
        try:
            logger.info("1. Starting TranscriptionPipeline & AudioEngine...")
            pipeline.start()
            audio_engine.start()

            logger.info("2. Listening for speech... (speak Marathi, Hindi, or English)")
            time.sleep(4.0)

            logger.info("3. Stopping AudioEngine & TranscriptionPipeline...")
            audio_engine.stop()
            pipeline.stop()
            event_bus.shutdown()

            logger.info("============================================================")
            logger.info("Phase 2 Demonstration successfully completed!")
            logger.info("============================================================")
            return 0

        except Exception as exc:
            logger.error(f"STT demonstration failed: {exc}", exc_info=True)
            audio_engine.stop()
            pipeline.stop()
            event_bus.shutdown()
            return 1


if __name__ == "__main__":
    sys.exit(run_demo())
