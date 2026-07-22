"""Demonstration script for Phase 8 Meeting Summarization Engine.

Demonstrates generating Executive Summary, Bullet Points, and Key Takeaways
from structured meeting context (transcripts + speakers + intelligence items).
"""

import json
import time

from core.event_bus import EventBus
from loguru import logger
from modules.meeting_intelligence.models import IntelligenceItemModel, ItemType
from modules.meeting_intelligence.repository import IntelligenceRepository
from modules.storage.db import DatabaseEngine
from modules.storage.models import SpeakerModel, TranscriptModel
from modules.storage.repositories import (
    MeetingRepository,
    SpeakerRepository,
    TranscriptRepository,
)
from modules.summary.events import SummaryGeneratedEvent
from modules.summary.summary_service import SummaryService


class DemoSummaryLLMProvider:
    """Mock LLM provider returning realistic structured summary JSON."""

    @property
    def model_id(self) -> str:
        return "demo-qwen3-4b-summary-v1"

    def generate(
        self,
        prompt: str,
        *,
        system: str = "",
        max_tokens: int = 2048,
    ) -> str:
        return json.dumps(
            {
                "executive_summary": (
                    "The EchoMind engineering team aligned on the Phase 8 "
                    "Summarization Engine architecture. Rahul confirmed Qwen 3 4B "
                    "MLX integration, Priya reviewed UI specs, and Prayag "
                    "approved prompt layer design."
                ),
                "bullet_points": [
                    "Adopted Qwen 3 4B via mlx-lm for text summarization",
                    "Created core/llm/prompts/ dedicated prompt engineering layer",
                    "Integrated Phase 7 structured intelligence into summary context",
                    "Priya will review frontend UI projections by Thursday",
                    "Rahul will deploy staging build by Friday",
                ],
                "key_takeaways": [
                    "Structured meeting data anchors prevent LLM hallucinations",
                    "Decoupled prompt layer enables versioning without code changes",
                    "Live and final summary generation workflows provide visibility",
                ],
            }
        )


def run_demo() -> None:
    """Execute Meeting Summarization Engine demonstration."""
    logger.info("=" * 60)
    logger.info("EchoMind Phase 8: Meeting Summarization Engine Demo")
    logger.info("=" * 60)

    # 1. Infrastructure setup
    db = DatabaseEngine(db_url="sqlite:///:memory:")
    db.init_db()
    bus = EventBus(max_workers=2)
    mock_llm = DemoSummaryLLMProvider()

    summary_events: list[SummaryGeneratedEvent] = []
    bus.subscribe(SummaryGeneratedEvent, lambda e: summary_events.append(e))

    service = SummaryService(llm=mock_llm, db_engine=db, event_bus=bus)

    # 2. Seed meeting session and speakers
    with db.session_scope() as session:
        meeting = MeetingRepository.create(session, "Phase 8 Architecture Sync")
        mid = meeting.id

        spk_rahul = SpeakerModel(
            meeting_id=mid,
            temporary_name="Speaker A",
            display_name="Rahul",
            color="#4F46E5",
        )
        spk_priya = SpeakerModel(
            meeting_id=mid,
            temporary_name="Speaker B",
            display_name="Priya",
            color="#10B981",
        )
        spk_prayag = SpeakerModel(
            meeting_id=mid,
            temporary_name="Speaker C",
            display_name="Prayag",
            color="#F59E0B",
        )
        SpeakerRepository.create(session, spk_rahul)
        SpeakerRepository.create(session, spk_priya)
        SpeakerRepository.create(session, spk_prayag)

        rahul_id = spk_rahul.id
        priya_id = spk_priya.id
        prayag_id = spk_prayag.id

    logger.info(f"\nMeeting: Phase 8 Architecture Sync (ID: {mid[:8]})")
    logger.info(
        f"Speakers: Rahul ({rahul_id[:8]}), Priya ({priya_id[:8]}), "
        f"Prayag ({prayag_id[:8]})"
    )

    # 3. Seed transcripts
    transcripts = [
        (0, 0.0, "en", "Welcome to Phase 8 Engine review.", rahul_id),
        (
            1,
            4.0,
            "en",
            "Building prompt engineering under core/llm/prompts.",
            prayag_id,
        ),
        (2, 8.5, "hi", "Namaste, main UI components design kar rahi hoon.", priya_id),
        (
            3,
            13.0,
            "en",
            "Priya, please review the UI projections by Thursday.",
            rahul_id,
        ),
        (4, 17.5, "en", "Rahul will handle staging build by Friday.", prayag_id),
        (5, 22.0, "mr", "Objective aahe ground truth pass karne.", prayag_id),
        (6, 26.5, "en", "Awesome work team, let's trigger summary.", rahul_id),
    ]

    with db.session_scope() as session:
        for seq, ts, lang, text, spk_id in transcripts:
            t = TranscriptModel(
                meeting_id=mid,
                sequence_number=seq,
                timestamp=ts,
                language=lang,
                original_text=text,
                speaker_id=spk_id,
            )
            TranscriptRepository.add(session, t)

    # 4. Seed Phase 7 structured intelligence items
    intel_items = [
        (
            ItemType.ACTION_ITEM.value,
            "Review UI summary projections",
            "Priya",
            "2026-07-24",
            "HIGH",
        ),
        (
            ItemType.ACTION_ITEM.value,
            "Deploy staging release build",
            "Rahul",
            "2026-07-25",
            "HIGH",
        ),
        (
            ItemType.DECISION.value,
            "Adopt core/llm/prompts/ prompt engineering layer",
            None,
            None,
            "MEDIUM",
        ),
        (
            ItemType.DEADLINE.value,
            "Phase 8 release ready by Friday",
            None,
            "2026-07-25",
            "HIGH",
        ),
    ]

    with db.session_scope() as session:
        for itype, content, assignee, due, priority in intel_items:
            item = IntelligenceItemModel(
                meeting_id=mid,
                item_type=itype,
                content=content,
                content_hash=f"hash_{itype}_{content[:5]}",
                assignee=assignee,
                due_date=due,
                priority=priority,
                source_text=content,
            )
            IntelligenceRepository.create(session, item)

    logger.info("\n1. Generating Live Meeting Summary...")
    live_summary = service.generate_live_summary(mid)
    if live_summary:
        logger.info(
            f"   Live Summary generated (ID: {live_summary.id[:8]}, "
            f"Version: {live_summary.model_version})"
        )

    logger.info("\n2. Generating Automatic Final Meeting Summary...")
    final_summary = service.generate_final_summary(mid)
    if final_summary:
        logger.info(
            f"   Final Summary generated (ID: {final_summary.id[:8]}, "
            f"Version: {final_summary.model_version})"
        )
        logger.info("\n" + "-" * 50)
        logger.info("EXECUTIVE SUMMARY:")
        logger.info(final_summary.executive_summary)

        logger.info("\nBULLET POINTS:")
        for pt in final_summary.get_bullet_points_list():
            logger.info(f"  • {pt}")

        logger.info("\nKEY TAKEAWAYS:")
        for kw in final_summary.get_key_takeaways_list():
            logger.info(f"  ★ {kw}")
        logger.info("-" * 50)

    logger.info("\n3. Testing Summary Regeneration...")
    regen_summary = service.regenerate_summary(mid)
    if regen_summary:
        logger.info(
            f"   Regenerated Summary (ID: {regen_summary.id[:8]}, "
            f"Version: {regen_summary.model_version})"
        )

    # 4. Verify EventBus notifications
    time.sleep(0.3)
    logger.info(f"\n4. Events Received on EventBus: {len(summary_events)}")
    for evt in summary_events:
        mode = "Final" if evt.is_final else "Live"
        logger.info(f"   Event -> {mode} Summary Generated (ID: {evt.summary_id[:8]})")

    bus.shutdown()
    db.close()

    logger.info("\n" + "=" * 60)
    logger.info("Phase 8 Demo completed successfully!")
    logger.info("=" * 60)


if __name__ == "__main__":
    run_demo()
