"""Interactive demo script for Phase 4 Translation Engine.

Demonstrates decoupled EventBus worker routing:
TranscriptEvent (Marathi/Hindi) -> TranslationService Worker -> TranslationEvent.
"""

import sys
import time

from core.event_bus import EventBus
from loguru import logger
from modules.storage.service import TranscriptService
from modules.stt.transcript_event import (
    LANG_ENGLISH,
    LANG_HINDI,
    LANG_MARATHI,
    TranscriptEvent,
)
from modules.translation.service import TranslationService
from modules.translation.translation_event import TranslationEvent


def on_translation_display(evt: TranslationEvent) -> None:
    """EventBus subscriber callback handling TranslationEvent display output.

    Args:
        evt: TranslationEvent payload.
    """
    logger.info(
        f"TRANSLATION WORKER >> #{evt.sequence_number:02d} "
        f"[{evt.source_language.upper()}->{evt.target_language.upper()}]: "
        f"'{evt.original_text}' ==> '{evt.translated_text}'"
    )


def run_demo() -> int:
    """Run interactive 5-second translation event worker demonstration.

    Returns:
        int: Process exit code.
    """
    logger.info("============================================================")
    logger.info("EchoMind Phase 4: Independent Translation Worker Demo")
    logger.info("============================================================")

    # 1. Initialize EventBus, TranscriptService, and TranslationService
    event_bus = EventBus(max_workers=3)
    transcript_service = TranscriptService(event_bus=event_bus)
    translation_service = TranslationService(event_bus=event_bus)

    # 2. Subscribe UI listener to TranslationEvent
    event_bus.subscribe(TranslationEvent, on_translation_display)

    try:
        # 3. Start Meeting and Translation Worker
        logger.info("1. Starting Meeting Session and Translation Service Worker...")
        meeting = transcript_service.start_meeting("Multilingual Translation Sync")
        translation_service.start()

        # 4. Emit TranscriptEvents (Marathi, Hindi, English)
        logger.info("2. Emitting TranscriptEvents onto EventBus...")
        events = [
            TranscriptEvent(
                text="Shubh prabhat. Kasa ahes?",
                language=LANG_MARATHI,
                start_time=100.0,
                end_time=103.0,
                confidence=0.96,
                is_final=True,
                sequence_number=1,
            ),
            TranscriptEvent(
                text="Namaste, aap kaise hain?",
                language=LANG_HINDI,
                start_time=104.0,
                end_time=107.0,
                confidence=0.95,
                is_final=True,
                sequence_number=2,
            ),
            TranscriptEvent(
                text="Aajcha mukhya vishay Prayag ne design keleli architecture ahe.",
                language=LANG_MARATHI,
                start_time=108.0,
                end_time=112.0,
                confidence=0.98,
                is_final=True,
                sequence_number=3,
            ),
            TranscriptEvent(
                text="This English transcript will be skipped by translation worker.",
                language=LANG_ENGLISH,
                start_time=113.0,
                end_time=116.0,
                confidence=0.99,
                is_final=True,
                sequence_number=4,
            ),
        ]

        for evt in events:
            seq = evt.sequence_number
            lang = evt.language.upper()
            logger.info(
                f"STT Pipeline Emitted Transcript #{seq} [{lang}]: '{evt.text}'"
            )
            event_bus.publish(evt)
            time.sleep(0.1)

        time.sleep(0.4)

        # 5. Stop services
        logger.info("3. Stopping Translation Worker & Meeting Session...")
        translation_service.stop()
        transcript_service.end_meeting(meeting.id)
        event_bus.shutdown()

        logger.info("============================================================")
        logger.info("Phase 4 Demonstration successfully completed!")
        logger.info("============================================================")
        return 0

    except Exception as exc:
        logger.error(f"Translation demonstration failed: {exc}", exc_info=True)
        translation_service.stop()
        event_bus.shutdown()
        return 1


if __name__ == "__main__":
    sys.exit(run_demo())
