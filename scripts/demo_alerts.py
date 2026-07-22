"""Interactive demo script for Phase 5 Real-Time Intelligence & Alert System.

Demonstrates multilingual trigger matching (Prayag, प्रायग, Deadline, Urgent),
RuleEngine evaluation, macOS desktop notifications, sound alerts, and SQLite.
"""

import sys
import time

from core.event_bus import EventBus
from loguru import logger
from modules.intelligence.alert_manager import AlertEvent, AlertManager
from modules.intelligence.notification_service import NotificationService
from modules.storage.service import TranscriptService
from modules.stt.transcript_event import (
    LANG_ENGLISH,
    LANG_MARATHI,
    TranscriptEvent,
)


def on_alert_display(evt: AlertEvent) -> None:
    """EventBus subscriber callback rendering colorized AlertEvent display output.

    Args:
        evt: AlertEvent payload.
    """
    logger.warning(
        f"INTELLIGENCE ALERT [{evt.severity}] >> Rule: '{evt.rule_name}' | "
        f"Trigger: '{evt.trigger_keyword}' | Text: {evt.highlighted_text}"
    )


def run_demo() -> int:
    """Run interactive real-time intelligence and alert demonstration.

    Returns:
        int: Process exit code.
    """
    logger.info("============================================================")
    logger.info("EchoMind Phase 5: Real-Time Intelligence & Alert Engine Demo")
    logger.info("============================================================")

    # 1. Initialize EventBus, NotificationService, TranscriptService, and AlertManager
    event_bus = EventBus(max_workers=3)
    notification_service = NotificationService(play_sound_enabled=True)
    transcript_service = TranscriptService(event_bus=event_bus)
    alert_manager = AlertManager(
        event_bus=event_bus,
        notification_service=notification_service,
    )

    # 2. Subscribe UI display listener to AlertEvent
    event_bus.subscribe(AlertEvent, on_alert_display)

    try:
        # 3. Start Meeting and AlertManager Worker
        logger.info("1. Starting Meeting Session and AlertManager Worker...")
        meeting = transcript_service.start_meeting("EchoMind Intelligence Verification")
        alert_manager.start()

        # 4. Emit TranscriptEvents triggering rules
        logger.info("2. Emitting TranscriptEvents onto EventBus...")
        events = [
            TranscriptEvent(
                text="Prayag joined the engineering sync.",
                language=LANG_ENGLISH,
                start_time=100.0,
                end_time=103.0,
                confidence=0.98,
                is_final=True,
                sequence_number=1,
            ),
            TranscriptEvent(
                text="आजच्या सत्राचे नेतृत्व प्रयाग करत आहेत.",
                language=LANG_MARATHI,
                start_time=104.0,
                end_time=107.0,
                confidence=0.95,
                is_final=True,
                sequence_number=2,
            ),
            TranscriptEvent(
                text="This feature is Urgent and has a strict Deadline tomorrow.",
                language=LANG_ENGLISH,
                start_time=108.0,
                end_time=111.0,
                confidence=0.99,
                is_final=True,
                sequence_number=3,
            ),
            TranscriptEvent(
                text="CRITICAL: Deployment to Production environment starting now.",
                language=LANG_ENGLISH,
                start_time=112.0,
                end_time=115.0,
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
            time.sleep(0.2)

        time.sleep(0.5)

        # 5. Stop services
        logger.info("3. Stopping AlertManager & Meeting Session...")
        alert_manager.stop()
        transcript_service.end_meeting(meeting.id)
        event_bus.shutdown()

        logger.info("============================================================")
        logger.info("Phase 5 Demonstration successfully completed!")
        logger.info("============================================================")
        return 0

    except Exception as exc:
        logger.error(f"Intelligence demonstration failed: {exc}", exc_info=True)
        alert_manager.stop()
        event_bus.shutdown()
        return 1


if __name__ == "__main__":
    sys.exit(run_demo())
