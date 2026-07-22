"""Tests for Meeting Intelligence Engine (Phase 7).

Covers extraction, parsing, validation, dedup, repository,
and the incremental + final reconciliation pipeline.
"""

import json
import time

import pytest
from core.event_bus import EventBus
from modules.meeting_intelligence.events import IntelligenceExtractedEvent
from modules.meeting_intelligence.intelligence_service import IntelligenceService
from modules.meeting_intelligence.models import (
    IntelligenceItemModel,
    IntelligenceResponse,
    ItemType,
    ParsedItem,
    compute_content_hash,
)
from modules.meeting_intelligence.parser import parse_llm_response
from modules.meeting_intelligence.prompt_builder import build_extraction_prompt
from modules.meeting_intelligence.repository import IntelligenceRepository
from modules.storage.db import DatabaseEngine
from modules.storage.models import TranscriptModel
from modules.storage.repositories import MeetingRepository, TranscriptRepository

# ── Mock LLM Provider ──


class MockLLMProvider:
    """Mock LLM that returns canned JSON responses."""

    def __init__(self, response: str = "") -> None:
        self._response = response
        self._call_count = 0

    @property
    def model_id(self) -> str:
        return "mock-llm-v1"

    def generate(
        self,
        prompt: str,
        *,
        system: str = "",
        max_tokens: int = 2048,
    ) -> str:
        self._call_count += 1
        return self._response


VALID_LLM_RESPONSE = json.dumps(
    {
        "items": [
            {
                "type": "ACTION_ITEM",
                "content": "Deploy hotfix to staging",
                "assignee": "Rahul",
                "due_date": "2026-07-25",
                "priority": "HIGH",
                "confidence": 0.95,
                "source_text": "Rahul, deploy the hotfix to staging by Friday",
            },
            {
                "type": "DECISION",
                "content": "Use SQLite for local storage",
                "confidence": 0.9,
                "source_text": "We decided to go with SQLite",
            },
            {
                "type": "DEADLINE",
                "content": "Phase 7 demo by next Tuesday",
                "due_date": "2026-07-29",
                "priority": "HIGH",
                "confidence": 0.85,
                "source_text": "Demo must be ready by next Tuesday",
            },
            {
                "type": "QUESTION",
                "content": "Should we support Kannada?",
                "confidence": 0.7,
                "source_text": "Do we need Kannada support?",
            },
            {
                "type": "RISK",
                "content": "Model may exceed memory on 8GB Macs",
                "priority": "MEDIUM",
                "confidence": 0.8,
                "source_text": "8GB machines might struggle",
            },
            {
                "type": "FOLLOW_UP",
                "content": "Review Qwen benchmark results",
                "assignee": "Priya",
                "confidence": 0.75,
                "source_text": "Priya will review the benchmarks",
            },
        ]
    }
)


# ── Fixtures ──


@pytest.fixture
def memory_db():
    db = DatabaseEngine(db_url="sqlite:///:memory:")
    db.init_db()
    return db


@pytest.fixture
def event_bus():
    return EventBus(max_workers=1)


# ── Parser Tests ──


def test_parse_valid_json():
    """Parse well-formed LLM JSON response."""
    items = parse_llm_response(VALID_LLM_RESPONSE)
    assert len(items) == 6
    types = {i.type for i in items}
    assert types == {
        "ACTION_ITEM",
        "DECISION",
        "DEADLINE",
        "QUESTION",
        "RISK",
        "FOLLOW_UP",
    }


def test_parse_json_with_markdown_fences():
    """Parse JSON wrapped in markdown code fences."""
    fenced = f"```json\n{VALID_LLM_RESPONSE}\n```"
    items = parse_llm_response(fenced)
    assert len(items) == 6


def test_parse_malformed_json():
    """Malformed JSON returns empty list, no crash."""
    items = parse_llm_response("{broken json here")
    assert items == []


def test_parse_truncated_json():
    """Truncated JSON returns empty list."""
    truncated = '{"items": [{"type": "ACTION_ITEM", "content": "dep'
    items = parse_llm_response(truncated)
    assert items == []


def test_parse_empty_items():
    """Empty items array returns empty list."""
    items = parse_llm_response('{"items": []}')
    assert items == []


def test_parse_unknown_type_filtered():
    """Unknown item types are filtered out."""
    data = json.dumps({"items": [{"type": "UNKNOWN_TYPE", "content": "test"}]})
    items = parse_llm_response(data)
    assert items == []


def test_parse_mixed_valid_invalid_types():
    """Valid types kept, invalid types filtered."""
    data = json.dumps(
        {
            "items": [
                {"type": "ACTION_ITEM", "content": "valid"},
                {"type": "BOGUS", "content": "invalid"},
            ]
        }
    )
    items = parse_llm_response(data)
    assert len(items) == 1
    assert items[0].type == "ACTION_ITEM"


# ── Content Hash Tests ──


def test_content_hash_deterministic():
    """Same input produces same hash."""
    h1 = compute_content_hash("ACTION_ITEM", "Deploy hotfix")
    h2 = compute_content_hash("ACTION_ITEM", "Deploy hotfix")
    assert h1 == h2


def test_content_hash_case_insensitive():
    """Hash is case-insensitive."""
    h1 = compute_content_hash("ACTION_ITEM", "Deploy Hotfix")
    h2 = compute_content_hash("ACTION_ITEM", "deploy hotfix")
    assert h1 == h2


def test_content_hash_type_matters():
    """Different types produce different hashes."""
    h1 = compute_content_hash("ACTION_ITEM", "test")
    h2 = compute_content_hash("DECISION", "test")
    assert h1 != h2


# ── Prompt Builder Tests ──


def test_prompt_builder_empty_transcripts():
    """Empty transcript list produces fallback prompt."""
    sys, user = build_extraction_prompt([])
    assert "No transcript content" in user


def test_prompt_builder_formats_transcripts(memory_db):
    """Prompt builder formats transcript lines correctly."""
    with memory_db.session_scope() as session:
        meeting = MeetingRepository.create(session, "Test")
        t = TranscriptModel(
            meeting_id=meeting.id,
            sequence_number=1,
            timestamp=5.0,
            language="en",
            original_text="Let's deploy the hotfix",
        )
        TranscriptRepository.add(session, t)
        transcripts = TranscriptRepository.get_by_meeting(session, meeting.id)

    sys_prompt, user_prompt = build_extraction_prompt(transcripts)
    assert "5.0s" in user_prompt
    assert "deploy the hotfix" in user_prompt
    assert "JSON" in sys_prompt


# ── Repository Tests ──


def test_repository_create_and_retrieve(memory_db):
    """Create and retrieve intelligence items."""
    with memory_db.session_scope() as session:
        meeting = MeetingRepository.create(session, "Repo Test")
        item = IntelligenceItemModel(
            meeting_id=meeting.id,
            item_type=ItemType.ACTION_ITEM.value,
            content="Test action",
            content_hash=compute_content_hash(
                ItemType.ACTION_ITEM.value, "Test action"
            ),
            source_text="source",
        )
        IntelligenceRepository.create(session, item)

    with memory_db.session_scope() as session:
        items = IntelligenceRepository.get_by_meeting(session, meeting.id)
        assert len(items) == 1
        assert items[0].content == "Test action"


def test_repository_get_by_type(memory_db):
    """Filter items by type."""
    with memory_db.session_scope() as session:
        meeting = MeetingRepository.create(session, "Type Test")
        for t in [ItemType.ACTION_ITEM, ItemType.DECISION]:
            item = IntelligenceItemModel(
                meeting_id=meeting.id,
                item_type=t.value,
                content=f"Test {t.value}",
                content_hash=compute_content_hash(t.value, f"Test {t.value}"),
                source_text="src",
            )
            IntelligenceRepository.create(session, item)

    with memory_db.session_scope() as session:
        actions = IntelligenceRepository.get_by_type(
            session, meeting.id, ItemType.ACTION_ITEM.value
        )
        assert len(actions) == 1
        assert actions[0].item_type == ItemType.ACTION_ITEM.value


def test_repository_exists_by_hash(memory_db):
    """Dedup hash detection works."""
    content_hash = compute_content_hash("RISK", "Memory issue")
    with memory_db.session_scope() as session:
        meeting = MeetingRepository.create(session, "Dedup Test")
        mid = meeting.id

        assert not IntelligenceRepository.exists_by_hash(
            session, mid, "RISK", content_hash
        )

        item = IntelligenceItemModel(
            meeting_id=mid,
            item_type="RISK",
            content="Memory issue",
            content_hash=content_hash,
            source_text="src",
        )
        IntelligenceRepository.create(session, item)

        assert IntelligenceRepository.exists_by_hash(session, mid, "RISK", content_hash)


def test_repository_delete_non_final(memory_db):
    """Delete non-final items for reconciliation."""
    with memory_db.session_scope() as session:
        meeting = MeetingRepository.create(session, "Final Test")
        mid = meeting.id

        # Incremental item (is_final=0)
        i1 = IntelligenceItemModel(
            meeting_id=mid,
            item_type="ACTION_ITEM",
            content="Incremental",
            content_hash=compute_content_hash("ACTION_ITEM", "Incremental"),
            source_text="src",
            is_final=0,
        )
        # Final item (is_final=1)
        i2 = IntelligenceItemModel(
            meeting_id=mid,
            item_type="DECISION",
            content="Final decision",
            content_hash=compute_content_hash("DECISION", "Final decision"),
            source_text="src",
            is_final=1,
        )
        IntelligenceRepository.create(session, i1)
        IntelligenceRepository.create(session, i2)

    with memory_db.session_scope() as session:
        deleted = IntelligenceRepository.delete_non_final(session, mid)
        assert deleted == 1

    with memory_db.session_scope() as session:
        remaining = IntelligenceRepository.get_by_meeting(session, mid)
        assert len(remaining) == 1
        assert remaining[0].is_final == 1


# ── IntelligenceService Tests ──


def test_service_extract_final(memory_db, event_bus):
    """Full extraction pipeline with mock LLM."""
    mock_llm = MockLLMProvider(VALID_LLM_RESPONSE)

    # Seed meeting and transcripts
    with memory_db.session_scope() as session:
        meeting = MeetingRepository.create(session, "Service Test")
        mid = meeting.id
        for i in range(5):
            t = TranscriptModel(
                meeting_id=mid,
                sequence_number=i,
                timestamp=float(i * 3),
                language="en",
                original_text=f"Transcript segment {i}",
            )
            TranscriptRepository.add(session, t)

    service = IntelligenceService(
        llm=mock_llm,
        db_engine=memory_db,
        event_bus=event_bus,
    )

    count = service.extract_final(mid)
    assert count == 6
    assert mock_llm._call_count == 1

    with memory_db.session_scope() as session:
        items = IntelligenceRepository.get_by_meeting(session, mid)
        assert len(items) == 6
        assert all(i.is_final == 1 for i in items)


def test_service_empty_transcripts(memory_db, event_bus):
    """No LLM call when meeting has no transcripts."""
    mock_llm = MockLLMProvider(VALID_LLM_RESPONSE)

    with memory_db.session_scope() as session:
        meeting = MeetingRepository.create(session, "Empty Test")
        mid = meeting.id

    service = IntelligenceService(
        llm=mock_llm,
        db_engine=memory_db,
        event_bus=event_bus,
    )

    count = service.extract_final(mid)
    assert count == 0
    assert mock_llm._call_count == 0


def test_service_malformed_llm_output(memory_db, event_bus):
    """Malformed LLM output produces zero items, no crash."""
    mock_llm = MockLLMProvider("{broken garbage}")

    with memory_db.session_scope() as session:
        meeting = MeetingRepository.create(session, "Bad LLM")
        mid = meeting.id
        t = TranscriptModel(
            meeting_id=mid,
            sequence_number=0,
            timestamp=0.0,
            language="en",
            original_text="Some text",
        )
        TranscriptRepository.add(session, t)

    service = IntelligenceService(
        llm=mock_llm,
        db_engine=memory_db,
        event_bus=event_bus,
    )
    count = service.extract_final(mid)
    assert count == 0


def test_service_duplicate_detection(memory_db, event_bus):
    """Second extraction skips already-persisted items."""
    mock_llm = MockLLMProvider(VALID_LLM_RESPONSE)

    with memory_db.session_scope() as session:
        meeting = MeetingRepository.create(session, "Dedup Service")
        mid = meeting.id
        t = TranscriptModel(
            meeting_id=mid,
            sequence_number=0,
            timestamp=0.0,
            language="en",
            original_text="Some transcript",
        )
        TranscriptRepository.add(session, t)

    service = IntelligenceService(
        llm=mock_llm,
        db_engine=memory_db,
        event_bus=event_bus,
    )

    count1 = service.extract_final(mid)
    assert count1 == 6

    # Second extraction should find all as duplicates
    count2 = service.extract_final(mid)
    # delete_non_final removes 0 (all are final), then re-extract
    # but content_hash dedup prevents re-insertion
    assert count2 == 0


def test_service_incremental_window(memory_db, event_bus):
    """Incremental extraction respects window_size threshold."""
    mock_llm = MockLLMProvider(VALID_LLM_RESPONSE)

    with memory_db.session_scope() as session:
        meeting = MeetingRepository.create(session, "Window Test")
        mid = meeting.id
        # Add only 3 transcripts (below default window=20)
        for i in range(3):
            t = TranscriptModel(
                meeting_id=mid,
                sequence_number=i,
                timestamp=float(i),
                language="en",
                original_text=f"Segment {i}",
            )
            TranscriptRepository.add(session, t)

    service = IntelligenceService(
        llm=mock_llm,
        db_engine=memory_db,
        event_bus=event_bus,
    )

    # Below window threshold
    count = service.extract_incremental(mid, window_size=5)
    assert count == 0
    assert mock_llm._call_count == 0

    # At window threshold
    with memory_db.session_scope() as session:
        for i in range(3, 8):
            t = TranscriptModel(
                meeting_id=mid,
                sequence_number=i,
                timestamp=float(i),
                language="en",
                original_text=f"Segment {i}",
            )
            TranscriptRepository.add(session, t)

    count = service.extract_incremental(mid, window_size=5)
    assert count > 0


def test_service_event_published(memory_db, event_bus):
    """IntelligenceExtractedEvent is published on extraction."""
    mock_llm = MockLLMProvider(VALID_LLM_RESPONSE)
    received: list[IntelligenceExtractedEvent] = []
    event_bus.subscribe(
        IntelligenceExtractedEvent,
        lambda e: received.append(e),
    )

    with memory_db.session_scope() as session:
        meeting = MeetingRepository.create(session, "Event Test")
        mid = meeting.id
        t = TranscriptModel(
            meeting_id=mid,
            sequence_number=0,
            timestamp=0.0,
            language="en",
            original_text="Test text",
        )
        TranscriptRepository.add(session, t)

    service = IntelligenceService(
        llm=mock_llm,
        db_engine=memory_db,
        event_bus=event_bus,
    )
    service.extract_final(mid)

    # Give event bus thread a moment
    time.sleep(0.2)
    assert len(received) == 1
    assert received[0].meeting_id == mid
    assert received[0].is_final is True
    assert received[0].item_count == 6


# ── Pydantic Schema Validation Tests ──


def test_parsed_item_defaults():
    """ParsedItem fills defaults correctly."""
    item = ParsedItem(type="ACTION_ITEM", content="test")
    assert item.assignee is None
    assert item.confidence == 0.8
    assert item.source_text == ""


def test_intelligence_response_empty():
    """IntelligenceResponse accepts empty items."""
    resp = IntelligenceResponse(items=[])
    assert resp.items == []


def test_intelligence_response_validation():
    """IntelligenceResponse validates from dict."""
    data = {
        "items": [
            {"type": "DECISION", "content": "Use Qwen"},
        ]
    }
    resp = IntelligenceResponse.model_validate(data)
    assert len(resp.items) == 1
