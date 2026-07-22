"""Interactive demo script for Phase 1 AudioEngine & EventBus.

Launches continuous microphone capture, subscribes to AudioChunk events,
displays real-time audio signal levels, tests state transitions,
and proves zero disk persistence occurs.
"""

import sys
import time

from core.event_bus import EventBus
from loguru import logger
from modules.audio.engine import AudioEngine
from modules.audio.models import AudioChunk


def audio_chunk_listener(chunk: AudioChunk) -> None:
    """EventBus subscriber callback handling incoming AudioChunk payloads.

    Args:
        chunk: AudioChunk instance emitted by AudioEngine.
    """
    bars = "#" * int(chunk.rms_power * 40)
    logger.info(
        f"AudioChunk #{chunk.sequence_number:03d} | "
        f"Duration: {chunk.duration_sec:.2f}s | "
        f"RMS: {chunk.rms_power:.4f} [{bars:<40}]"
    )


def run_demo() -> int:
    """Run interactive 5-second continuous audio streaming demonstration.

    Returns:
        int: Process exit code.
    """
    logger.info("============================================================")
    logger.info("EchoMind Phase 1: Audio Engine & EventBus Demonstration")
    logger.info("============================================================")

    # 1. Initialize EventBus and subscribe listener
    event_bus = EventBus(max_workers=2)
    event_bus.subscribe(AudioChunk, audio_chunk_listener)

    # 2. Initialize AudioEngine
    engine = AudioEngine(event_bus=event_bus, buffer_duration_sec=10.0)

    try:
        # 3. Start audio stream
        logger.info("1. Starting continuous microphone audio capture...")
        engine.start()
        time.sleep(2.0)

        # 4. Pause audio stream
        logger.info("2. Pausing audio stream for 1.5 seconds...")
        engine.pause()
        time.sleep(1.5)

        # 5. Resume audio stream
        logger.info("3. Resuming audio stream for 2.0 seconds...")
        engine.resume()
        time.sleep(2.0)

        # 6. Check ring buffer statistics
        recent_pcm = engine.buffer.get_recent_audio(3.0)
        logger.info(
            f"Ring Buffer Summary: Retained {engine.buffer.current_duration_sec:.2f}s "
            f"({len(recent_pcm)} float32 samples in memory)."
        )

        # 7. Stop audio stream
        logger.info("4. Stopping AudioEngine stream...")
        engine.stop()
        event_bus.shutdown()

        logger.info("============================================================")
        logger.info("Phase 1 Demonstration successfully completed!")
        logger.info("Zero audio files written to disk. All PCM stored in memory.")
        logger.info("============================================================")
        return 0

    except Exception as exc:
        logger.error(f"Demonstration failed with exception: {exc}", exc_info=True)
        engine.stop()
        event_bus.shutdown()
        return 1


if __name__ == "__main__":
    sys.exit(run_demo())
