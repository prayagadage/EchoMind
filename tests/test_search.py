"""Unit and integration test suite for Local Semantic Search & Knowledge Base."""

import pytest
from core.event_bus import EventBus
from core.vector.base import VectorRecord
from core.vector.sqlite_provider import SQLiteVectorStore
from modules.meeting_intelligence.models import IntelligenceItemModel, ItemType
from modules.meeting_intelligence.repository import IntelligenceRepository
from modules.search.embedding_service import LocalSemanticEmbeddingProvider
from modules.search.indexer import KnowledgeIndexer
from modules.search.models import SearchEntityType
from modules.search.search_service import SearchService
from modules.storage.db import DatabaseEngine
from modules.storage.models import SpeakerModel, TranscriptModel
from modules.storage.repositories import (
    MeetingRepository,
    SpeakerRepository,
    TranscriptRepository,
)
from modules.summary.models import MeetingSummaryModel, SummaryType
from modules.summary.repository import SummaryRepository


@pytest.fixture
def memory_db():
    db = DatabaseEngine(db_url="sqlite:///:memory:")
    db.init_db()
    return db


@pytest.fixture
def event_bus():
    return EventBus(max_workers=1)


@pytest.fixture
def vector_store():
    return SQLiteVectorStore(db_url="sqlite:///:memory:")


@pytest.fixture
def embedding_service():
    return LocalSemanticEmbeddingProvider()


# ── Embedding Service Tests ──


def test_embedding_generation_and_normalization(embedding_service):
    """Test embedding generation produces 384-dim normalized L2 vector."""
    vec = embedding_service.embed_text("Deploy hotfix to production staging")
    assert len(vec) == 384
    norm = sum(x * x for x in vec) ** 0.5
    assert pytest.approx(norm, 0.001) == 1.0


def test_embedding_empty_string(embedding_service):
    """Empty string returns 384-dim zero vector."""
    vec = embedding_service.embed_text("   ")
    assert len(vec) == 384
    assert all(x == 0.0 for x in vec)


# ── VectorStore Tests ──


def test_vector_store_add_search_delete(vector_store, embedding_service):
    """Test SQLiteVectorStore insert, similarity search, and deletion by meeting."""
    v1 = embedding_service.embed_text("Deploy hotfix release to production")
    v2 = embedding_service.embed_text("Casual lunch conversation")

    rec1 = VectorRecord(
        id="rec-1",
        vector=v1,
        content="Deploy hotfix release to production",
        entity_type=SearchEntityType.ACTION_ITEM.value,
        meeting_id="m-100",
        source_id="src-1",
    )
    rec2 = VectorRecord(
        id="rec-2",
        vector=v2,
        content="Casual lunch conversation",
        entity_type=SearchEntityType.TRANSCRIPT.value,
        meeting_id="m-100",
        source_id="src-2",
    )

    vector_store.add_records([rec1, rec2])
    assert vector_store.count() == 2

    # Query matching rec1
    q_vec = embedding_service.embed_text("production deployment hotfix")
    hits = vector_store.search(q_vec, top_k=2)

    assert len(hits) == 2
    assert hits[0].record.id == "rec-1"
    assert hits[0].score > hits[1].score

    # Delete meeting vectors
    deleted = vector_store.delete_by_meeting("m-100")
    assert deleted == 2
    assert vector_store.count() == 0


def test_vector_store_empty_search(vector_store, embedding_service):
    """Search empty VectorStore returns empty hits list."""
    q_vec = embedding_service.embed_text("test query")
    hits = vector_store.search(q_vec, top_k=5)
    assert hits == []


# ── Indexer & SearchService Integration Tests ──


def test_indexer_and_search_service_pipeline(
    memory_db, event_bus, vector_store, embedding_service
):
    """Test end-to-end indexing of transcripts, summaries, and action items."""
    indexer = KnowledgeIndexer(
        embedding_service=embedding_service,
        vector_store=vector_store,
        db_engine=memory_db,
        event_bus=event_bus,
    )
    search_service = SearchService(
        embedding_service=embedding_service,
        vector_store=vector_store,
        db_engine=memory_db,
    )

    # 1. Seed meeting data
    with memory_db.session_scope() as session:
        meeting = MeetingRepository.create(session, "Security Review")
        mid = meeting.id

        speaker = SpeakerModel(
            meeting_id=mid,
            temporary_name="Speaker A",
            display_name="Rahul",
        )
        SpeakerRepository.create(session, speaker)

        # Transcripts (Marathi translated text + English text)
        t1 = TranscriptModel(
            meeting_id=mid,
            sequence_number=1,
            timestamp=0.0,
            language="mr",
            original_text="Aapla main objective security vulnerability fix karne aahe.",
            translated_text="Our main objective is to fix the security vulnerability.",
            speaker_id=speaker.id,
        )
        t2 = TranscriptModel(
            meeting_id=mid,
            sequence_number=2,
            timestamp=5.0,
            language="en",
            original_text="Priya will audit the API authentication logic.",
            speaker_id=speaker.id,
        )
        TranscriptRepository.add(session, t1)
        TranscriptRepository.add(session, t2)

        # Summary
        summary = MeetingSummaryModel(
            meeting_id=mid,
            summary_type=SummaryType.COMBINED.value,
            executive_summary="Team focused on fixing security vulnerabilities.",
            key_takeaways='["Authentication logic must be audited by Priya"]',
            is_final=1,
        )
        SummaryRepository.create(session, summary)

        # Action item
        item = IntelligenceItemModel(
            meeting_id=mid,
            item_type=ItemType.ACTION_ITEM.value,
            content="Audit API authentication logic",
            content_hash="hash_audit_api",
            assignee="Priya",
            source_text="Priya will audit the API authentication logic.",
        )
        IntelligenceRepository.create(session, item)

    # 2. Run indexer
    count = indexer.index_meeting(mid)
    assert count == 4  # 2 transcripts + 1 summary + 1 action item

    # 3. Perform semantic search for security vulnerabilities
    results = search_service.search("security vulnerability fix", top_k=5)
    assert len(results) > 0
    top_hit = results[0]
    assert (
        "security" in top_hit.content.lower()
        or "vulnerability" in top_hit.content.lower()
    )
    assert top_hit.meeting_title == "Security Review"

    # 4. Search with entity_type filter
    actions_only = search_service.search(
        "authentication logic", entity_type=ItemType.ACTION_ITEM.value
    )
    assert len(actions_only) == 1
    assert actions_only[0].entity_type == ItemType.ACTION_ITEM.value


def test_indexer_duplicate_prevention(
    memory_db, event_bus, vector_store, embedding_service
):
    """Indexer skips re-indexing identical records based on content hash."""
    indexer = KnowledgeIndexer(
        embedding_service=embedding_service,
        vector_store=vector_store,
        db_engine=memory_db,
        event_bus=event_bus,
    )

    with memory_db.session_scope() as session:
        meeting = MeetingRepository.create(session, "Dedup Meeting")
        mid = meeting.id
        t = TranscriptModel(
            meeting_id=mid,
            sequence_number=1,
            timestamp=0.0,
            language="en",
            original_text="Deduplication test segment.",
        )
        TranscriptRepository.add(session, t)

    count1 = indexer.index_meeting(mid)
    assert count1 == 1

    # Second indexing pass skips duplicate
    count2 = indexer.index_meeting(mid)
    assert count2 == 0


def test_search_service_meeting_id_filter(
    memory_db, event_bus, vector_store, embedding_service
):
    """SearchService restricts search results to specified meeting_id."""
    indexer = KnowledgeIndexer(
        embedding_service=embedding_service,
        vector_store=vector_store,
        db_engine=memory_db,
        event_bus=event_bus,
    )
    search_service = SearchService(
        embedding_service=embedding_service,
        vector_store=vector_store,
        db_engine=memory_db,
    )

    with memory_db.session_scope() as session:
        m1 = MeetingRepository.create(session, "Meeting 1")
        m2 = MeetingRepository.create(session, "Meeting 2")

        t1 = TranscriptModel(
            meeting_id=m1.id,
            sequence_number=1,
            timestamp=0.0,
            language="en",
            original_text="Database migration plan.",
        )
        t2 = TranscriptModel(
            meeting_id=m2.id,
            sequence_number=1,
            timestamp=0.0,
            language="en",
            original_text="Database migration plan.",
        )
        TranscriptRepository.add(session, t1)
        TranscriptRepository.add(session, t2)

    indexer.index_meeting(m1.id)
    indexer.index_meeting(m2.id)

    # Filter search to m1
    results = search_service.search("database migration", meeting_id=m1.id)
    assert len(results) == 1
    assert results[0].meeting_id == m1.id
