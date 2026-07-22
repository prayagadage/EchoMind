"""Interactive demo script for Phase 6A Speaker Segmentation.

Demonstrates speaker change detection, label assignment (Speaker A, B),
speaker continuity tracking across utterances, and SQLite persistence.
"""

import sys
import time

import numpy as np
from core.event_bus import EventBus
from loguru import logger
from modules.audio.models import AudioChunk
from modules.speaker.speaker_events import (
    SpeakerAssignedEvent,
    SpeakerChangedEvent,
)
from modules.speaker.speaker_service import SpeakerService
from modules.storage.service import TranscriptService
from modules.stt.transcript_event import (
    LANG_ENGLISH,
    LANG_MARATHI,
    TranscriptEvent,
)


def on_speaker_changed(evt: SpeakerChangedEvent) -> None:
    """EventBus callback rendering speaker transition."""
    prev = evt.previous_speaker_id[:8] if evt.previous_speaker_id else "None"
    name = evt.new_temporary_name
    sid = evt.new_speaker_id[:8]
    logger.info(f"SPEAKER CHANGED >> Previous: {prev} ===> New: {name} ({sid})")


def on_speaker_assigned(evt: SpeakerAssignedEvent) -> None:
    """EventBus callback rendering transcript speaker assignment."""
    tid = evt.transcript_id[:8]
    logger.warning(f"SPEAKER LINKED >> Transcript {tid} linked to {evt.temporary_name}")


def generate_speaker_audio(
    freq: float, duration_sec: float = 0.5, sr: int = 16000
) -> np.ndarray:
    """Generate synthetic sine wave audio signal representing a speaker."""
    t = np.linspace(0, duration_sec, int(sr * duration_sec), endpoint=False)
    signal = 0.5 * np.sin(2 * np.pi * freq * t) + 0.3 * np.sin(
        2 * np.pi * (freq * 1.5) * t
    )
    return signal.astype(np.float32)


def run_demo() -> int:
    """Run interactive real-time speaker segmentation demonstration.

    Returns:
        int: Process exit code.
    """
    logger.info("============================================================")
    logger.info("EchoMind Phase 6A: Streaming Speaker Segmentation Demo")
    logger.info("============================================================")

    # 1. Initialize Infrastructure
    event_bus = EventBus(max_workers=3)
    transcript_service = TranscriptService(event_bus=event_bus)
    speaker_service = SpeakerService(event_bus=event_bus)

    # 2. Subscribe EventBus callbacks
    event_bus.subscribe(SpeakerChangedEvent, on_speaker_changed)
    event_bus.subscribe(SpeakerAssignedEvent, on_speaker_assigned)

    try:
        # 3. Start Meeting Session & Speaker Service
        logger.info("1. Starting Meeting Session and SpeakerService Worker...")
        meeting = transcript_service.start_meeting(
            "Multilingual Speaker Segmentation Sync"
        )
        speaker_service.set_active_meeting(meeting.id)
        speaker_service.start()

        # Frequencies representing 2 distinct speakers
        FREQ_SPEAKER_A = 160.0  # Speaker A
        FREQ_SPEAKER_B = 440.0  # Speaker B

        # Utterance sequence: A -> A -> B -> A -> B
        utterances = [
            (
                FREQ_SPEAKER_A,
                "Hello everyone, welcome to the EchoMind architecture review.",
                LANG_ENGLISH,
            ),
            (
                FREQ_SPEAKER_A,
                "Today we are verifying speaker segmentation on Apple Silicon.",
                LANG_ENGLISH,
            ),
            (
                FREQ_SPEAKER_B,
                "नमस्कार, मी दुसऱ्या स्पीकरचे प्रतिनिधित्व करत आहे.",
                LANG_MARATHI,
            ),
            (
                FREQ_SPEAKER_A,
                "Thanks Speaker B! I am Speaker A speaking again.",
                LANG_ENGLISH,
            ),
            (
                FREQ_SPEAKER_B,
                "Great, the system successfully re-identified me as Speaker B!",
                LANG_ENGLISH,
            ),
        ]

        logger.info("2. Streaming Audio Chunks & TranscriptEvents...")
        for seq, (freq, text, lang) in enumerate(utterances, start=1):
            # A. Stream audio chunk
            audio_data = generate_speaker_audio(freq=freq, duration_sec=0.5)
            chunk = AudioChunk(
                data=audio_data,
                sample_rate=16000,
                channels=1,
                timestamp=time.time(),
                sequence_number=seq,
            )
            event_bus.publish(chunk)
            time.sleep(0.1)

            # B. Stream STT transcript event
            t_evt = TranscriptEvent(
                text=text,
                language=lang,
                start_time=float(seq),
                end_time=float(seq) + 1.0,
                confidence=0.98,
                is_final=True,
                sequence_number=seq,
            )
            logger.info(f"STT Emitted Transcript #{seq} [{lang.upper()}]: '{text}'")
            event_bus.publish(t_evt)
            time.sleep(0.3)

        time.sleep(0.5)

        # 4. Stop Services & End Meeting
        logger.info("3. Stopping SpeakerService & Meeting Session...")
        speaker_service.stop()
        transcript_service.end_meeting(meeting.id)
        event_bus.shutdown()

        logger.info("============================================================")
        logger.info("Phase 6A Demonstration successfully completed!")
        logger.info("============================================================")
        return 0

    except Exception as exc:
        logger.error(f"Speaker demonstration failed: {exc}", exc_info=True)
        speaker_service.stop()
        event_bus.shutdown()
        return 1


if __name__ == "__main__":
    sys.exit(run_demo())
