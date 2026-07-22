"""Unit tests for Phase 3 Storage and Transcript Management package."""

import time

import pytest
from core.event_bus import EventBus
from modules.storage.db import DatabaseEngine
from modules.storage.models import MeetingStatus
from modules.storage.repositories import MeetingRepository, TranscriptRepository
from modules.storage.service import TranscriptService
from modules.stt.transcript_event import LANG_ENGLISH, LANG_MARATHI, TranscriptEvent


@pytest.fixture
def memory_db() -> DatabaseEngine:
    """Provide isolated in-memory DatabaseEngine instance."""
    engine = DatabaseEngine(db_url="sqlite:///:memory:")
    engine.init_db()
    return engine


def test_db_engine_session_scope(memory_db: DatabaseEngine) -> None:
    """Verify DatabaseEngine session_scope creates tables and handles transactions."""
    with memory_db.session_scope() as session:
        m = MeetingRepository.create(session, "Test Meeting Scope")
        assert m.id is not None
        assert m.title == "Test Meeting Scope"


def test_meeting_repository_crud(memory_db: DatabaseEngine) -> None:
    """Verify MeetingRepository CRUD and lifecycle operations."""
    with memory_db.session_scope() as session:
        meeting = MeetingRepository.create(session, "Quarterly Sync")
        meeting_id = meeting.id

    with memory_db.session_scope() as session:
        retrieved = MeetingRepository.get_by_id(session, meeting_id)
        assert retrieved is not None
        assert retrieved.status == MeetingStatus.IN_PROGRESS.value

        active_list = MeetingRepository.list_active(session)
        assert len(active_list) == 1

        ended = MeetingRepository.end_meeting(session, meeting_id)
        assert ended is not None
        assert ended.status == MeetingStatus.ENDED.value
        assert ended.ended_at is not None


def test_transcript_repository_add_and_search(memory_db: DatabaseEngine) -> None:
    """Verify TranscriptRepository persistence and keyword search."""
    with memory_db.session_scope() as session:
        meeting = MeetingRepository.create(session, "Search Test Meeting")
        meeting_id = meeting.id

        event1 = TranscriptEvent(
            text="Prayag discussed the roadmap.",
            language=LANG_ENGLISH,
            start_time=100.0,
            end_time=102.0,
            confidence=0.95,
            is_final=True,
            sequence_number=1,
        )
        event2 = TranscriptEvent(
            text="Aajcha agenda khup mahatvacha ahe.",
            language=LANG_MARATHI,
            start_time=103.0,
            end_time=105.0,
            confidence=0.92,
            is_final=True,
            sequence_number=2,
        )

        from modules.storage.models import TranscriptModel

        t1 = TranscriptModel(
            meeting_id=meeting_id,
            sequence_number=event1.sequence_number,
            timestamp=event1.start_time,
            language=event1.language,
            original_text=event1.text,
            confidence=event1.confidence,
        )
        t2 = TranscriptModel(
            meeting_id=meeting_id,
            sequence_number=event2.sequence_number,
            timestamp=event2.start_time,
            language=event2.language,
            original_text=event2.text,
            confidence=event2.confidence,
        )

        TranscriptRepository.add(session, t1)
        TranscriptRepository.add(session, t2)

    with memory_db.session_scope() as session:
        # Search by keyword 'Prayag'
        results = TranscriptRepository.search_by_keyword(session, "Prayag")
        assert len(results) == 1
        assert results[0].original_text == "Prayag discussed the roadmap."

        # Search Marathi keyword 'agenda'
        results_mr = TranscriptRepository.search_by_keyword(session, "agenda")
        assert len(results_mr) == 1
        assert results_mr[0].language == LANG_MARATHI


def test_transcript_service_event_bus_auto_persistence(
    memory_db: DatabaseEngine,
) -> None:
    """Verify TranscriptService auto-persists TranscriptEvents emitted on EventBus."""
    bus = EventBus(max_workers=2)
    service = TranscriptService(db_engine=memory_db, event_bus=bus)

    # 1. Start meeting session
    meeting = service.start_meeting("EventBus Auto-Persist Meeting")
    meeting_id = meeting.id
    assert service.active_meeting_id == meeting_id

    # 2. Emit TranscriptEvent onto EventBus (Speech module doesn't touch DB directly)
    event = TranscriptEvent(
        text="Automatic EventBus persistence test.",
        language=LANG_ENGLISH,
        start_time=500.0,
        end_time=502.0,
        confidence=0.99,
        is_final=True,
        sequence_number=1,
    )
    bus.publish(event)

    # Wait briefly for EventBus worker thread execution
    time.sleep(0.2)

    # 3. Retrieve meeting transcripts from SQLite database
    retrieved_meeting = service.get_meeting(meeting_id)
    assert retrieved_meeting is not None
    assert len(retrieved_meeting.transcripts) == 1
    assert (
        retrieved_meeting.transcripts[0].original_text
        == "Automatic EventBus persistence test."
    )

    # 4. End meeting
    service.end_meeting(meeting_id)
    assert service.active_meeting_id is None

    bus.shutdown()
