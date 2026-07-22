"""Interactive demonstration script for Phase 3 Transcript Storage System.

Demonstrates Meeting lifecycle management, automatic EventBus transcript persistence,
SQLite database storage, and keyword search capabilities.
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


def run_demo() -> int:
    """Run interactive demonstration of Phase 3 persistent storage.

    Returns:
        int: Process exit code.
    """
    logger.info("============================================================")
    logger.info("EchoMind Phase 3: Persistent Memory & Storage Demonstration")
    logger.info("============================================================")

    # 1. Initialize EventBus and TranscriptService
    event_bus = EventBus(max_workers=2)
    service = TranscriptService(event_bus=event_bus)

    try:
        # 2. Start new meeting
        logger.info("1. Starting new meeting session...")
        meeting = service.start_meeting("EchoMind Architecture Review")
        logger.info(f"Active Meeting Created: '{meeting.title}' (ID: {meeting.id})")

        # 3. Simulate emitting TranscriptEvents from STT pipeline onto EventBus
        logger.info(
            "2. Emitting TranscriptEvents onto EventBus (Auto-persisting to SQLite)..."
        )
        events = [
            TranscriptEvent(
                text="Welcome everyone to the EchoMind engineering sync.",
                language=LANG_ENGLISH,
                start_time=100.0,
                end_time=103.0,
                confidence=0.98,
                is_final=True,
                sequence_number=1,
            ),
            TranscriptEvent(
                text="Aajcha mukhya vishay Prayag ne design keleli architecture ahe.",
                language=LANG_MARATHI,
                start_time=104.0,
                end_time=108.0,
                confidence=0.95,
                is_final=True,
                sequence_number=2,
            ),
            TranscriptEvent(
                text="Hum speech recognition aur storage modules test kar rahe hain.",
                language=LANG_HINDI,
                start_time=109.0,
                end_time=113.0,
                confidence=0.96,
                is_final=True,
                sequence_number=3,
            ),
        ]

        for evt in events:
            logger.info(
                f"Emitting Event #{evt.sequence_number} "
                f"[{evt.language.upper()}]: '{evt.text}'"
            )
            event_bus.publish(evt)

        # Allow EventBus worker thread to execute auto-persistence
        time.sleep(0.3)

        # 4. Query meeting history from SQLite
        logger.info("3. Retrieving persisted meeting transcripts from SQLite...")
        persisted_meeting = service.get_meeting(meeting.id)
        if persisted_meeting:
            count = len(persisted_meeting.transcripts)
            logger.info(
                f"Retrieved Meeting '{persisted_meeting.title}': "
                f"{count} transcripts stored."
            )
            for t in persisted_meeting.transcripts:
                logger.info(
                    f"  - Seq #{t.sequence_number:02d} "
                    f"[{t.language.upper()}]: '{t.original_text}'"
                )

        # 5. Perform keyword search
        logger.info("4. Executing full-text search query for 'Prayag'...")
        search_results = service.search_transcripts("Prayag")
        logger.info(f"Found {len(search_results)} matching segment(s):")
        for res in search_results:
            logger.info(f"  Match: [{res.language.upper()}] '{res.original_text}'")

        # 6. End meeting
        logger.info("5. Ending meeting session...")
        service.end_meeting(meeting.id)
        event_bus.shutdown()

        logger.info("============================================================")
        logger.info("Phase 3 Storage Demonstration successfully completed!")
        logger.info("============================================================")
        return 0

    except Exception as exc:
        logger.error(f"Storage demonstration failed: {exc}", exc_info=True)
        event_bus.shutdown()
        return 1


if __name__ == "__main__":
    sys.exit(run_demo())
