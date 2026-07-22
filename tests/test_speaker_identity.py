"""Unit tests for Phase 6B Speaker Identity Management System."""

import time

import pytest
from core.event_bus import EventBus
from modules.speaker.speaker_events import SpeakerMergedEvent, SpeakerUpdatedEvent
from modules.speaker.speaker_identity_service import (
    SpeakerIdentityService,
)
from modules.speaker.speaker_merge_service import (
    SpeakerMergeService,
)
from modules.speaker.speaker_registry import SpeakerRegistry
from modules.speaker.speaker_statistics import SpeakerStatisticsCalculator
from modules.speaker.ui_adapter import SpeakerUIAdapter
from modules.storage.db import DatabaseEngine
from modules.storage.models import TranscriptModel
from modules.storage.repositories import MeetingRepository, TranscriptRepository
from modules.stt.transcript_event import LANG_ENGLISH, LANG_MARATHI
from sqlalchemy import select


@pytest.fixture
def memory_db() -> DatabaseEngine:
    """Provide in-memory DatabaseEngine instance."""
    engine = DatabaseEngine(db_url="sqlite:///:memory:")
    engine.init_db()
    return engine


def test_speaker_registry_and_color_assignment(memory_db: DatabaseEngine) -> None:
    """Verify SpeakerRegistry creates speakers with palette colors."""
    registry = SpeakerRegistry()
    with memory_db.session_scope() as session:
        m = MeetingRepository.create(session, "Registry Test")
        spk1 = registry.register_speaker(session, m.id, "Speaker A")
        spk2 = registry.register_speaker(session, m.id, "Speaker B")

        assert spk1.temporary_name == "Speaker A"
        assert spk2.temporary_name == "Speaker B"
        assert spk1.color == "#4F46E5"
        assert spk2.color == "#10B981"
        assert spk1.display_name is None

        fetched = registry.list_speakers(session, m.id)
        assert len(fetched) == 2


def test_rename_speaker_and_transcript_consistency(memory_db: DatabaseEngine) -> None:
    """Verify renaming a speaker reflects in UI projections cleanly."""
    bus = EventBus()
    identity_service = SpeakerIdentityService(db_engine=memory_db, event_bus=bus)
    registry = SpeakerRegistry()

    events: list[SpeakerUpdatedEvent] = []
    bus.subscribe(SpeakerUpdatedEvent, lambda evt: events.append(evt))

    with memory_db.session_scope() as session:
        m = MeetingRepository.create(session, "Rename Test")
        m_id = m.id
        spk = registry.register_speaker(session, m_id, "Speaker A")
        spk_id = spk.id

        t1 = TranscriptModel(
            meeting_id=m_id,
            speaker_id=spk_id,
            sequence_number=1,
            timestamp=1.0,
            language=LANG_ENGLISH,
            original_text="Hello architecture team.",
            confidence=0.98,
        )
        TranscriptRepository.add(session, t1)
        t1_id = t1.id

    # Projection before rename -> 'Speaker A'
    with memory_db.session_scope() as session:
        t1_model = session.scalar(
            select(TranscriptModel).where(TranscriptModel.id == t1_id)
        )
        assert t1_model is not None
        proj_before = SpeakerUIAdapter.project_transcript(session, t1_model)
        assert proj_before.effective_speaker_name == "Speaker A"
        assert proj_before.temporary_speaker_name == "Speaker A"

    # Execute Rename: 'Speaker A' -> 'Rahul'
    updated_spk = identity_service.rename_speaker(m_id, spk_id, "Rahul")
    assert updated_spk.display_name == "Rahul"

    time.sleep(0.1)
    bus.shutdown()

    assert len(events) == 1
    assert events[0].display_name == "Rahul"

    # Projection after rename -> 'Rahul' (dynamically projected, transcript unchanged)
    with memory_db.session_scope() as session:
        t1_model = session.scalar(
            select(TranscriptModel).where(TranscriptModel.id == t1_id)
        )
        assert t1_model is not None
        assert t1_model.original_text == "Hello architecture team."
        proj_after = SpeakerUIAdapter.project_transcript(session, t1_model)
        assert proj_after.effective_speaker_name == "Rahul"
        assert proj_after.temporary_speaker_name == "Speaker A"


def test_merge_speakers_and_transcript_relinking(memory_db: DatabaseEngine) -> None:
    """Verify merging Speaker C into Speaker A reassigns transcripts."""
    bus = EventBus()
    merge_service = SpeakerMergeService(db_engine=memory_db, event_bus=bus)
    registry = SpeakerRegistry()

    merge_events: list[SpeakerMergedEvent] = []
    bus.subscribe(SpeakerMergedEvent, lambda evt: merge_events.append(evt))

    with memory_db.session_scope() as session:
        m = MeetingRepository.create(session, "Merge Test")
        m_id = m.id
        spk_a = registry.register_speaker(session, m_id, "Speaker A")
        spk_c = registry.register_speaker(session, m_id, "Speaker C")
        a_id, c_id = spk_a.id, spk_c.id

        # 2 transcripts for Speaker A, 2 transcripts for Speaker C
        t1 = TranscriptModel(
            meeting_id=m_id,
            speaker_id=a_id,
            sequence_number=1,
            timestamp=1.0,
            language=LANG_ENGLISH,
            original_text="A speaks first.",
            confidence=0.9,
        )
        t2 = TranscriptModel(
            meeting_id=m_id,
            speaker_id=c_id,
            sequence_number=2,
            timestamp=3.0,
            language=LANG_ENGLISH,
            original_text="C interrupts here.",
            confidence=0.9,
        )
        t3 = TranscriptModel(
            meeting_id=m_id,
            speaker_id=c_id,
            sequence_number=3,
            timestamp=5.0,
            language=LANG_MARATHI,
            original_text="C continues.",
            confidence=0.9,
        )
        TranscriptRepository.add(session, t1)
        TranscriptRepository.add(session, t2)
        TranscriptRepository.add(session, t3)

    # Execute Merge: Speaker C -> Speaker A
    count = merge_service.merge_speakers(
        m_id, target_speaker_id=c_id, destination_speaker_id=a_id
    )
    assert count == 2

    time.sleep(0.1)
    bus.shutdown()

    assert len(merge_events) == 1
    assert merge_events[0].affected_transcripts_count == 2

    # Verify database state after merge
    with memory_db.session_scope() as session:
        # Speaker C deleted
        spk_c_db = registry.get_speaker(session, c_id)
        assert spk_c_db is None

        # Transcripts t2 and t3 now point to Speaker A
        t2_db = session.scalar(
            select(TranscriptModel).where(TranscriptModel.sequence_number == 2)
        )
        t3_db = session.scalar(
            select(TranscriptModel).where(TranscriptModel.sequence_number == 3)
        )
        assert t2_db is not None and t2_db.speaker_id == a_id
        assert t3_db is not None and t3_db.speaker_id == a_id

        # Projections render as Speaker A
        projs = SpeakerUIAdapter.project_meeting_transcripts(session, m_id)
        assert len(projs) == 3
        assert all(p.effective_speaker_name == "Speaker A" for p in projs)


def test_speaker_statistics_calculation(memory_db: DatabaseEngine) -> None:
    """Verify calculation of total speaking time, turn count, and turn durations."""
    registry = SpeakerRegistry()
    with memory_db.session_scope() as session:
        m = MeetingRepository.create(session, "Stats Test")
        m_id = m.id
        spk_a = registry.register_speaker(session, m_id, "Speaker A")
        a_id = spk_a.id

        # 3 turns with explicit timestamps: t=0s, t=4s, t=7s
        TranscriptRepository.add(
            session,
            TranscriptModel(
                meeting_id=m_id,
                speaker_id=a_id,
                sequence_number=1,
                timestamp=0.0,
                language=LANG_ENGLISH,
                original_text="Turn one.",
                confidence=0.9,
            ),
        )
        TranscriptRepository.add(
            session,
            TranscriptModel(
                meeting_id=m_id,
                speaker_id=a_id,
                sequence_number=2,
                timestamp=4.0,
                language=LANG_ENGLISH,
                original_text="Turn two.",
                confidence=0.9,
            ),
        )
        TranscriptRepository.add(
            session,
            TranscriptModel(
                meeting_id=m_id,
                speaker_id=a_id,
                sequence_number=3,
                timestamp=7.0,
                language=LANG_ENGLISH,
                original_text="Turn three.",
                confidence=0.9,
            ),
        )

        stats = SpeakerStatisticsCalculator.calculate_speaker_stats(session, m_id, a_id)
        assert stats is not None
        assert stats.turn_count == 3
        assert stats.total_speaking_time_seconds == 9.5  # 4s + 3s + 2.5s default
        assert stats.longest_turn_duration_seconds == 4.0
        assert stats.avg_turn_duration_seconds == 3.17


def test_timeline_generation(memory_db: DatabaseEngine) -> None:
    """Verify chronological timeline segment generation for UI rendering."""
    registry = SpeakerRegistry()
    with memory_db.session_scope() as session:
        m = MeetingRepository.create(session, "Timeline Test")
        m_id = m.id
        spk_a = registry.register_speaker(session, m_id, "Speaker A")
        spk_b = registry.register_speaker(session, m_id, "Speaker B")
        a_id, b_id = spk_a.id, spk_b.id

        TranscriptRepository.add(
            session,
            TranscriptModel(
                meeting_id=m_id,
                speaker_id=a_id,
                sequence_number=1,
                timestamp=0.0,
                language=LANG_ENGLISH,
                original_text="Speaker A speaking.",
                confidence=0.9,
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
                original_text="Speaker B replying.",
                confidence=0.9,
            ),
        )

        timeline = SpeakerStatisticsCalculator.generate_timeline(session, m_id)
        assert len(timeline) == 2

        seg1 = timeline[0]
        assert seg1.speaker_id == a_id
        assert seg1.effective_name == "Speaker A"
        assert seg1.color == "#4F46E5"
        assert seg1.start_time == 0.0
        assert seg1.end_time == 3.0

        seg2 = timeline[1]
        assert seg2.speaker_id == b_id
        assert seg2.effective_name == "Speaker B"
        assert seg2.color == "#10B981"
        assert seg2.start_time == 3.0
        assert seg2.end_time == 5.5
