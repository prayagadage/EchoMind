"""Unit and integration test suite for Meeting Summarization Engine (Phase 8)."""

import json

import pytest
from core.event_bus import EventBus
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
from modules.summary.models import (
    MeetingSummaryModel,
    SummaryType,
)
from modules.summary.parser import parse_summary_response
from modules.summary.repository import SummaryRepository
from modules.summary.summary_builder import SummaryBuilder
from modules.summary.summary_service import SummaryService


class MockSummaryLLMProvider:
    """Mock LLM provider returning canned summary JSON."""

    def __init__(self, response: str = "") -> None:
        self._response = response
        self.call_count = 0

    @property
    def model_id(self) -> str:
        return "mock-summary-qwen-v1"

    def generate(
        self,
        prompt: str,
        *,
        system: str = "",
        max_tokens: int = 2048,
    ) -> str:
        self.call_count += 1
        return self._response


VALID_SUMMARY_RESPONSE = json.dumps(
    {
        "executive_summary": (
            "The team discussed Phase 8 implementation and agreed on Qwen 3 4B."
        ),
        "bullet_points": [
            "Qwen 3 4B selected as the default local LLM for summaries",
            "Structured meeting context anchors summary generation",
            "Rahul will deploy the staging release by Friday",
        ],
        "key_takeaways": [
            "Transcripts with ground-truth intelligence prevent hallucinations",
            "Pydantic schemas guarantee valid output structures",
        ],
    }
)


@pytest.fixture
def memory_db():
    db = DatabaseEngine(db_url="sqlite:///:memory:")
    db.init_db()
    return db


@pytest.fixture
def event_bus():
    return EventBus(max_workers=1)


# ── Parser Tests ──


def test_parse_valid_summary_json():
    """Parse valid LLM JSON output into SummaryResponseSchema."""
    parsed = parse_summary_response(VALID_SUMMARY_RESPONSE)
    assert "Phase 8 implementation" in parsed.executive_summary
    assert len(parsed.bullet_points) == 3
    assert len(parsed.key_takeaways) == 2


def test_parse_fenced_summary_json():
    """Parse Markdown-fenced LLM JSON output."""
    fenced = f"```json\n{VALID_SUMMARY_RESPONSE}\n```"
    parsed = parse_summary_response(fenced)
    assert len(parsed.bullet_points) == 3


def test_parse_malformed_summary_json_fallback():
    """Malformed LLM text falls back to raw executive summary text."""
    raw = "The meeting concluded with all members agreeing on the architectural plan."
    parsed = parse_summary_response(raw)
    assert parsed.executive_summary == raw
    assert parsed.bullet_points == []
    assert parsed.key_takeaways == []


# ── SummaryBuilder Tests ──


def test_summary_builder_aggregates_context(memory_db):
    """SummaryBuilder gathers transcripts, speakers, and intelligence items."""
    with memory_db.session_scope() as session:
        meeting = MeetingRepository.create(session, "Sprint Planning")
        mid = meeting.id

        speaker = SpeakerModel(
            meeting_id=mid,
            temporary_name="Speaker A",
            display_name="Rahul",
        )
        SpeakerRepository.create(session, speaker)

        t = TranscriptModel(
            meeting_id=mid,
            sequence_number=1,
            timestamp=0.0,
            language="en",
            original_text="We need to finalize the roadmap.",
            speaker_id=speaker.id,
        )
        TranscriptRepository.add(session, t)

        item = IntelligenceItemModel(
            meeting_id=mid,
            item_type=ItemType.ACTION_ITEM.value,
            content="Finalize roadmap",
            content_hash="hash123",
            assignee="Rahul",
            source_text="We need to finalize the roadmap.",
        )
        IntelligenceRepository.create(session, item)

    with memory_db.session_scope() as session:
        context = SummaryBuilder.build_context(session, mid)
        assert context.title == "Sprint Planning"
        assert len(context.speakers) == 1
        assert len(context.transcripts) == 1
        assert len(context.intelligence_items) == 1

        speakers_text = context.format_speakers_text()
        assert "Rahul" in speakers_text

        intel_text = context.format_intelligence_text()
        assert "Finalize roadmap" in intel_text
        assert "Assignee: Rahul" in intel_text


# ── Repository Tests ──


def test_summary_repository_crud(memory_db):
    """Test SummaryRepository create, get_latest, delete_non_final, and update."""
    with memory_db.session_scope() as session:
        meeting = MeetingRepository.create(session, "Repo Test")
        mid = meeting.id

        summary = MeetingSummaryModel(
            meeting_id=mid,
            summary_type=SummaryType.COMBINED.value,
            executive_summary="Initial live summary",
            bullet_points=json.dumps(["Point 1"]),
            key_takeaways=json.dumps(["Takeaway 1"]),
            is_final=0,
        )
        SummaryRepository.create(session, summary)
        sid = summary.id

    with memory_db.session_scope() as session:
        latest = SummaryRepository.get_latest(session, mid)
        assert latest is not None
        assert latest.id == sid
        assert latest.executive_summary == "Initial live summary"

        # Update summary
        updated = SummaryRepository.update(
            session,
            summary_id=sid,
            executive_summary="Updated executive summary",
            bullet_points=["Point 1", "Point 2"],
            key_takeaways=["Takeaway 1"],
            is_final=True,
        )
        assert updated is not None
        assert updated.executive_summary == "Updated executive summary"
        assert updated.is_final == 1

    with memory_db.session_scope() as session:
        # Create non-final summary and test delete_non_final
        s2 = MeetingSummaryModel(
            meeting_id=mid,
            summary_type=SummaryType.COMBINED.value,
            executive_summary="Temp summary",
            is_final=0,
        )
        SummaryRepository.create(session, s2)

    with memory_db.session_scope() as session:
        deleted_count = SummaryRepository.delete_non_final(session, mid)
        assert deleted_count == 1


# ── SummaryService Tests ──


def test_summary_service_live_and_final(memory_db, event_bus):
    """SummaryService generates live and final summaries."""
    mock_llm = MockSummaryLLMProvider(VALID_SUMMARY_RESPONSE)
    service = SummaryService(llm=mock_llm, db_engine=memory_db, event_bus=event_bus)

    with memory_db.session_scope() as session:
        meeting = MeetingRepository.create(session, "Architecture Sync")
        mid = meeting.id

        t = TranscriptModel(
            meeting_id=mid,
            sequence_number=1,
            timestamp=0.0,
            language="en",
            original_text="Let's approve Phase 8 design.",
        )
        TranscriptRepository.add(session, t)

    # 1. Live summary
    live_summary = service.generate_live_summary(mid)
    assert live_summary is not None
    assert live_summary.is_final == 0
    assert "Phase 8 implementation" in live_summary.executive_summary
    assert len(live_summary.get_bullet_points_list()) == 3

    # 2. Final summary
    final_summary = service.generate_final_summary(mid)
    assert final_summary is not None
    assert final_summary.is_final == 1
    assert mock_llm.call_count == 2


def test_summary_service_empty_meeting(memory_db, event_bus):
    """Empty meeting returns None and makes no LLM call."""
    mock_llm = MockSummaryLLMProvider(VALID_SUMMARY_RESPONSE)
    service = SummaryService(llm=mock_llm, db_engine=memory_db, event_bus=event_bus)

    with memory_db.session_scope() as session:
        meeting = MeetingRepository.create(session, "Empty Meeting")
        mid = meeting.id

    summary = service.generate_final_summary(mid)
    assert summary is None
    assert mock_llm.call_count == 0


def test_summary_service_meeting_without_action_items(memory_db, event_bus):
    """Summarize meeting that has transcripts but no pre-extracted action items."""
    mock_llm = MockSummaryLLMProvider(VALID_SUMMARY_RESPONSE)
    service = SummaryService(llm=mock_llm, db_engine=memory_db, event_bus=event_bus)

    with memory_db.session_scope() as session:
        meeting = MeetingRepository.create(session, "General Discussion")
        mid = meeting.id
        t = TranscriptModel(
            meeting_id=mid,
            sequence_number=1,
            timestamp=0.0,
            language="en",
            original_text="We had a casual catchup on Q3 goals.",
        )
        TranscriptRepository.add(session, t)

    summary = service.generate_final_summary(mid)
    assert summary is not None
    assert mock_llm.call_count == 1


def test_summary_service_regeneration(memory_db, event_bus):
    """SummaryService supports summary regeneration with incremented model version."""
    mock_llm = MockSummaryLLMProvider(VALID_SUMMARY_RESPONSE)
    service = SummaryService(llm=mock_llm, db_engine=memory_db, event_bus=event_bus)

    with memory_db.session_scope() as session:
        meeting = MeetingRepository.create(session, "Regen Meeting")
        mid = meeting.id
        t = TranscriptModel(
            meeting_id=mid,
            sequence_number=1,
            timestamp=0.0,
            language="en",
            original_text="Discussion point.",
        )
        TranscriptRepository.add(session, t)

    s1 = service.generate_final_summary(mid)
    assert s1 is not None
    assert s1.model_version == "1.0"

    s2 = service.regenerate_summary(mid)
    assert s2 is not None
    assert s2.model_version == "1.1"


def test_summary_event_published(memory_db, event_bus):
    """Verify SummaryGeneratedEvent is published when summary is generated."""
    mock_llm = MockSummaryLLMProvider(VALID_SUMMARY_RESPONSE)
    events: list[SummaryGeneratedEvent] = []
    event_bus.subscribe(SummaryGeneratedEvent, lambda e: events.append(e))

    service = SummaryService(llm=mock_llm, db_engine=memory_db, event_bus=event_bus)

    with memory_db.session_scope() as session:
        meeting = MeetingRepository.create(session, "Event Test Meeting")
        mid = meeting.id
        t = TranscriptModel(
            meeting_id=mid,
            sequence_number=1,
            timestamp=0.0,
            language="en",
            original_text="Testing event publication.",
        )
        TranscriptRepository.add(session, t)

    service.generate_final_summary(mid)

    # Wait briefly for threadpool execution
    import time

    time.sleep(0.2)

    assert len(events) == 1
    assert events[0].meeting_id == mid
    assert events[0].is_final is True
