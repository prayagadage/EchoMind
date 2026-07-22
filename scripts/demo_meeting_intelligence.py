"""Demo script for Meeting Intelligence Engine (Phase 7).

Demonstrates incremental + final extraction pipeline using a mock LLM.
"""

import json
import time

from core.event_bus import EventBus
from loguru import logger
from modules.meeting_intelligence.events import IntelligenceExtractedEvent
from modules.meeting_intelligence.intelligence_service import IntelligenceService
from modules.meeting_intelligence.models import ItemType
from modules.meeting_intelligence.repository import IntelligenceRepository
from modules.storage.db import DatabaseEngine
from modules.storage.models import SpeakerModel, TranscriptModel
from modules.storage.repositories import (
    MeetingRepository,
    SpeakerRepository,
    TranscriptRepository,
)


class DemoLLMProvider:
    """Mock LLM for demo purposes."""

    @property
    def model_id(self) -> str:
        return "demo-mock-v1"

    def generate(
        self,
        prompt: str,
        *,
        system: str = "",
        max_tokens: int = 2048,
    ) -> str:
        return json.dumps(
            {
                "items": [
                    {
                        "type": "ACTION_ITEM",
                        "content": "Deploy hotfix to staging by Friday",
                        "assignee": "Rahul",
                        "due_date": "2026-07-25",
                        "priority": "HIGH",
                        "confidence": 0.95,
                        "source_text": "Rahul, deploy the hotfix to staging by Friday",
                    },
                    {
                        "type": "DECISION",
                        "content": "Use Qwen 3 4B for meeting intelligence",
                        "confidence": 0.9,
                        "source_text": "We decided to go with Qwen 3 4B",
                    },
                    {
                        "type": "DEADLINE",
                        "content": "Phase 7 demo ready by next Tuesday",
                        "due_date": "2026-07-29",
                        "priority": "HIGH",
                        "confidence": 0.85,
                        "source_text": "The demo must be ready by Tuesday",
                    },
                    {
                        "type": "QUESTION",
                        "content": "Should we support Kannada in Phase 8?",
                        "confidence": 0.7,
                        "source_text": "Do we need Kannada support?",
                    },
                    {
                        "type": "RISK",
                        "content": "4B model may exceed memory on 8GB MacBooks",
                        "priority": "MEDIUM",
                        "confidence": 0.8,
                        "source_text": "8GB machines might struggle with the model",
                    },
                    {
                        "type": "FOLLOW_UP",
                        "content": "Review Qwen benchmark results next week",
                        "assignee": "Priya",
                        "confidence": 0.75,
                        "source_text": "Priya will review the benchmarks",
                    },
                ]
            }
        )


def run_demo() -> None:
    """Execute Meeting Intelligence Engine demonstration."""
    logger.info("=" * 60)
    logger.info("EchoMind Phase 7: Meeting Intelligence Engine Demo")
    logger.info("=" * 60)

    # Setup
    db = DatabaseEngine(db_url="sqlite:///:memory:")
    db.init_db()
    bus = EventBus(max_workers=2)
    mock_llm = DemoLLMProvider()

    events_received: list[IntelligenceExtractedEvent] = []
    bus.subscribe(
        IntelligenceExtractedEvent,
        lambda e: events_received.append(e),
    )

    service = IntelligenceService(llm=mock_llm, db_engine=db, event_bus=bus)

    # Create meeting with speakers
    with db.session_scope() as session:
        meeting = MeetingRepository.create(session, "Phase 7 Review")
        mid = meeting.id

        rahul = SpeakerModel(
            meeting_id=mid,
            temporary_name="Speaker A",
            display_name="Rahul",
            color="#4F46E5",
        )
        priya = SpeakerModel(
            meeting_id=mid,
            temporary_name="Speaker B",
            display_name="Priya",
            color="#10B981",
        )
        SpeakerRepository.create(session, rahul)
        SpeakerRepository.create(session, priya)
        rahul_id = rahul.id
        priya_id = priya.id

    logger.info(f"\nMeeting: Phase 7 Review (ID: {mid[:8]})")
    logger.info(f"Speakers: Rahul ({rahul_id[:8]}), Priya ({priya_id[:8]})")

    # Simulate transcript segments
    segments = [
        (0, 0.0, "en", "Welcome everyone to the Phase 7 review.", rahul_id),
        (
            1,
            3.5,
            "en",
            "We decided to go with Qwen 3 4B for meeting intelligence.",
            rahul_id,
        ),
        (
            2,
            7.0,
            "en",
            "Rahul, please deploy the hotfix to staging by Friday.",
            priya_id,
        ),
        (3, 11.0, "en", "The demo must be ready by Tuesday.", rahul_id),
        (4, 14.5, "en", "Do we need Kannada support?", priya_id),
        (5, 18.0, "en", "8GB machines might struggle with the model.", rahul_id),
        (6, 22.0, "en", "Priya will review the benchmarks next week.", rahul_id),
        (7, 25.0, "en", "Great meeting, let's wrap up.", priya_id),
    ]

    with db.session_scope() as session:
        for seq, ts, lang, text, spk_id in segments:
            t = TranscriptModel(
                meeting_id=mid,
                sequence_number=seq,
                timestamp=ts,
                language=lang,
                original_text=text,
                speaker_id=spk_id,
            )
            TranscriptRepository.add(session, t)

    # 1. Incremental extraction (window=5)
    logger.info("\n1. Incremental Extraction (window=5)...")
    inc_count = service.extract_incremental(mid, window_size=5)
    logger.info(f"   Extracted {inc_count} items (incremental)")

    # 2. Final reconciliation
    logger.info("\n2. Final Reconciliation Pass...")
    final_count = service.extract_final(mid)
    logger.info(f"   Extracted {final_count} items (final)")

    # 3. Display extracted items
    logger.info("\n3. Extracted Meeting Intelligence:")
    with db.session_scope() as session:
        items = IntelligenceRepository.get_by_meeting(session, mid)
        for item in items:
            prefix = "✓" if item.is_final else "~"
            logger.info(
                f"   {prefix} [{item.item_type}] {item.content}"
                + (f" → {item.assignee}" if item.assignee else "")
                + (f" (by {item.due_date})" if item.due_date else "")
            )

    # 4. Query by type
    logger.info("\n4. Action Items Only:")
    with db.session_scope() as session:
        actions = IntelligenceRepository.get_by_type(
            session, mid, ItemType.ACTION_ITEM.value
        )
        for a in actions:
            logger.info(
                f"   → {a.content} [Assignee: {a.assignee}] "
                f"[Due: {a.due_date}] [Priority: {a.priority}]"
            )

    # 5. Event verification
    time.sleep(0.3)
    logger.info(f"\n5. Events received: {len(events_received)}")
    for evt in events_received:
        mode = "Final" if evt.is_final else "Incremental"
        logger.info(f"   {mode}: {evt.item_count} items, " f"types={evt.item_types}")

    bus.shutdown()
    logger.info("\n" + "=" * 60)
    logger.info("Phase 7 Demo completed successfully!")
    logger.info("=" * 60)


if __name__ == "__main__":
    run_demo()
