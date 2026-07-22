"""Interactive demo script for Phase 6B Speaker Identity Management System."""

import sys
import time

from core.event_bus import EventBus
from loguru import logger
from modules.speaker.speaker_events import SpeakerMergedEvent, SpeakerUpdatedEvent
from modules.speaker.speaker_identity_service import SpeakerIdentityService
from modules.speaker.speaker_merge_service import SpeakerMergeService
from modules.speaker.speaker_registry import SpeakerRegistry
from modules.speaker.speaker_statistics import SpeakerStatisticsCalculator
from modules.speaker.ui_adapter import SpeakerUIAdapter
from modules.storage.db import DatabaseEngine
from modules.storage.models import TranscriptModel
from modules.storage.repositories import MeetingRepository, TranscriptRepository
from modules.stt.transcript_event import LANG_ENGLISH, LANG_MARATHI


def run_demo() -> int:
    """Execute Phase 6B Speaker Identity Management System Demonstration.

    Returns:
        int: Process exit status code.
    """
    logger.info("============================================================")
    logger.info("EchoMind Phase 6B: Speaker Identity Management System Demo")
    logger.info("============================================================")

    # 1. Setup in-memory Database & EventBus
    db_engine = DatabaseEngine(db_url="sqlite:///:memory:")
    db_engine.init_db()
    event_bus = EventBus(max_workers=2)

    registry = SpeakerRegistry()
    identity_service = SpeakerIdentityService(db_engine=db_engine, event_bus=event_bus)
    merge_service = SpeakerMergeService(db_engine=db_engine, event_bus=event_bus)

    # Subscribe to identity events
    event_bus.subscribe(
        SpeakerUpdatedEvent,
        lambda evt: logger.warning(
            f"EVENT >> Speaker Updated: {evt.temporary_name} ({evt.speaker_id[:8]}) "
            f"-> DisplayName: '{evt.display_name}', Color: {evt.color}"
        ),
    )
    event_bus.subscribe(
        SpeakerMergedEvent,
        lambda evt: logger.warning(
            f"EVENT >> Speaker Merged: Target {evt.target_speaker_id[:8]} "
            f"-> Destination {evt.destination_speaker_id[:8]} "
            f"(Affected Segments: {evt.affected_transcripts_count})"
        ),
    )

    try:
        # 2. Start Meeting & Register Speakers
        logger.info("\n1. Registering Detected Meeting Speakers...")
        with db_engine.session_scope() as session:
            m = MeetingRepository.create(session, "Architecture Sync")
            m_id = m.id
            spk_a = registry.register_speaker(session, m_id, "Speaker A")
            spk_b = registry.register_speaker(session, m_id, "Speaker B")
            spk_c = registry.register_speaker(session, m_id, "Speaker C")
            a_id, b_id, c_id = spk_a.id, spk_b.id, spk_c.id

            # Add transcripts
            TranscriptRepository.add(
                session,
                TranscriptModel(
                    meeting_id=m_id,
                    speaker_id=a_id,
                    sequence_number=1,
                    timestamp=0.0,
                    language=LANG_ENGLISH,
                    original_text="Welcome team to Phase 6B review.",
                    confidence=0.98,
                ),
            )
            TranscriptRepository.add(
                session,
                TranscriptModel(
                    meeting_id=m_id,
                    speaker_id=b_id,
                    sequence_number=2,
                    timestamp=3.0,
                    language=LANG_ENGLISH,
                    original_text="Priya here, frontend projections ready.",
                    confidence=0.97,
                ),
            )
            TranscriptRepository.add(
                session,
                TranscriptModel(
                    meeting_id=m_id,
                    speaker_id=c_id,
                    sequence_number=3,
                    timestamp=6.5,
                    language=LANG_MARATHI,
                    original_text="नमस्कार, मी तिसऱ्या स्पीकरचे विधान जोडत आहे.",
                    confidence=0.95,
                ),
            )
            TranscriptRepository.add(
                session,
                TranscriptModel(
                    meeting_id=m_id,
                    speaker_id=a_id,
                    sequence_number=4,
                    timestamp=10.0,
                    language=LANG_ENGLISH,
                    original_text="Awesome work everyone!",
                    confidence=0.99,
                ),
            )

        # 3. Rename Speakers
        logger.info(
            "\n2. User Renaming Speakers (Speaker A -> Rahul, Speaker B -> Priya)..."
        )
        identity_service.rename_speaker(m_id, a_id, "Rahul")
        identity_service.rename_speaker(m_id, b_id, "Priya")
        identity_service.set_speaker_color(
            m_id, a_id, "#10B981"
        )  # Emerald Green for Rahul
        time.sleep(0.1)

        # 4. Project Transcripts for UI
        logger.info("\n3. Rendering Dynamic UI Transcript Projections...")
        with db_engine.session_scope() as session:
            projections = SpeakerUIAdapter.project_meeting_transcripts(session, m_id)
            for p in projections:
                name = p.effective_speaker_name
                color = p.speaker_color
                lang = p.language.upper()
                txt = p.original_text
                logger.info(
                    f"[{p.sequence_number}] {name:<8} ({color}) [{lang}]: '{txt}'"
                )

        # 5. Merge Speaker C into Rahul
        logger.info("\n4. Merging Anonymous Speaker C into Rahul...")
        merge_service.merge_speakers(
            m_id, target_speaker_id=c_id, destination_speaker_id=a_id
        )
        time.sleep(0.1)

        # 6. Compute Speaker Statistics
        logger.info("\n5. Computing Meeting Speaker Statistics...")
        with db_engine.session_scope() as session:
            stats_map = SpeakerStatisticsCalculator.calculate_meeting_stats(
                session, m_id
            )
            for _spk_id, st in stats_map.items():
                name = st.effective_name
                t_time = st.total_speaking_time_seconds
                turns = st.turn_count
                avg_dur = st.avg_turn_duration_seconds
                long_dur = st.longest_turn_duration_seconds
                logger.info(
                    f"SPEAKER STATS >> {name:<8} | Time: {t_time}s | "
                    f"Turns: {turns} | Avg: {avg_dur}s | Max: {long_dur}s"
                )

        # 7. Generate Speaker Timeline Visualization
        logger.info("\n6. Generating Speaker Timeline Segments for UI...")
        with db_engine.session_scope() as session:
            timeline = SpeakerStatisticsCalculator.generate_timeline(session, m_id)
            for seg in timeline:
                st_t, end_t = seg.start_time, seg.end_time
                dur, name = seg.duration_seconds, seg.effective_name
                col, snip = seg.color, seg.text_snippet
                logger.info(
                    f"TIMELINE [{st_t:04.1f}s - {end_t:04.1f}s] ({dur}s) "
                    f"-> {name} [{col}]: '{snip}'"
                )

        event_bus.shutdown()
        logger.info("============================================================")
        logger.info("Phase 6B Demonstration successfully completed!")
        logger.info("============================================================")
        return 0

    except Exception as exc:
        logger.error(f"Phase 6B demonstration failed: {exc}", exc_info=True)
        event_bus.shutdown()
        return 1


if __name__ == "__main__":
    sys.exit(run_demo())
