"""Unit and integration test suite for AI Meeting Assistant (Phase 10)."""

import pytest
from core.event_bus import EventBus
from core.vector.sqlite_provider import SQLiteVectorStore
from modules.assistant.assistant_service import AssistantService
from modules.assistant.context_builder import ContextBuilder
from modules.assistant.conversation_memory import ConversationMemory
from modules.assistant.query_parser import QueryParser
from modules.assistant.retrieval_service import RetrievalService
from modules.meeting_intelligence.models import IntelligenceItemModel, ItemType
from modules.meeting_intelligence.repository import IntelligenceRepository
from modules.search.embedding_service import LocalSemanticEmbeddingProvider
from modules.search.indexer import KnowledgeIndexer
from modules.search.search_service import SearchService
from modules.storage.db import DatabaseEngine
from modules.storage.models import SpeakerModel, TranscriptModel
from modules.storage.repositories import (
    MeetingRepository,
    SpeakerRepository,
    TranscriptRepository,
)


class MockAssistantLLMProvider:
    """Mock LLM provider returning realistic grounded answer text."""

    def __init__(self, response: str = "") -> None:
        self.response = response
        self.call_count = 0

    @property
    def model_id(self) -> str:
        return "mock-assistant-qwen-v1"

    def generate(
        self,
        prompt: str,
        *,
        system: str = "",
        max_tokens: int = 2048,
    ) -> str:
        self.call_count += 1
        if self.response:
            return self.response
        return "According to [Ref 1], Rahul was assigned to deploy hotfix by Friday."


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


# ── QueryParser Tests ──


def test_query_parser_detects_action_item_intent():
    """QueryParser extracts action item target_entity_type."""
    parsed = QueryParser.parse("What action items were assigned to Priya?")
    assert parsed.target_entity_type == ItemType.ACTION_ITEM.value
    assert "action" in parsed.keywords


def test_query_parser_detects_decision_intent():
    """QueryParser extracts decision target_entity_type."""
    parsed = QueryParser.parse("What decisions did the team agree on?")
    assert parsed.target_entity_type == ItemType.DECISION.value


# ── ConversationMemory Tests ──


def test_conversation_memory_sliding_window():
    """ConversationMemory retains turns up to max_turns limit."""
    mem = ConversationMemory(max_turns=2)
    session_id = "sess-123"

    mem.add_turn(session_id, "Q1", "A1")
    mem.add_turn(session_id, "Q2", "A2")
    mem.add_turn(session_id, "Q3", "A3")

    history = mem.get_history(session_id)
    assert len(history) == 2
    assert history[0].user_query == "Q2"
    assert history[1].user_query == "Q3"

    formatted = mem.format_history_text(session_id)
    assert "User: Q2" in formatted
    assert "Assistant: A3" in formatted


# ── ContextBuilder Tests ──


def test_context_builder_formats_references(
    memory_db, event_bus, vector_store, embedding_service
):
    """ContextBuilder constructs [Ref N] tags and Citations list."""
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
        meeting = MeetingRepository.create(session, "Ref Test Meeting")
        mid = meeting.id
        t = TranscriptModel(
            meeting_id=mid,
            sequence_number=1,
            timestamp=10.0,
            language="en",
            original_text="Rahul will handle staging deployment.",
        )
        TranscriptRepository.add(session, t)

    indexer.index_meeting(mid)
    hits = search_service.search("Rahul staging deployment")

    payload = ContextBuilder.build_grounded_context(hits)
    assert "[Ref 1]" in payload.context_text
    assert len(payload.citations) == 1
    assert payload.citations[0].meeting_title == "Ref Test Meeting"


# ── AssistantService RAG Pipeline Tests ──


def test_assistant_service_rag_flow(
    memory_db, event_bus, vector_store, embedding_service
):
    """AssistantService executes end-to-end RAG query flow with citations."""
    mock_llm = MockAssistantLLMProvider()
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
    retrieval_service = RetrievalService(search_service=search_service)

    with memory_db.session_scope() as session:
        meeting = MeetingRepository.create(session, "Release Sync")
        mid = meeting.id

        speaker = SpeakerModel(
            meeting_id=mid,
            temporary_name="Speaker A",
            display_name="Rahul",
        )
        SpeakerRepository.create(session, speaker)

        item = IntelligenceItemModel(
            meeting_id=mid,
            item_type=ItemType.ACTION_ITEM.value,
            content="Deploy hotfix build by Friday",
            content_hash="hash_deploy_hotfix",
            assignee="Rahul",
            due_date="2026-07-25",
            source_text="Deploy hotfix build by Friday",
        )
        IntelligenceRepository.create(session, item)

    indexer.index_meeting(mid)

    service = AssistantService(
        llm=mock_llm,
        retrieval_service=retrieval_service,
    )

    session_id = "test-rag-session"
    response = service.ask(
        session_id=session_id, query="What action item was given to Rahul?"
    )

    assert response.session_id == session_id
    assert response.retrieved_count > 0
    assert "Rahul" in response.answer
    assert len(response.citations) > 0
    assert response.citations[0].meeting_title == "Release Sync"
    assert mock_llm.call_count == 1

    # Verify conversation memory turn recorded
    history = service.memory.get_history(session_id)
    assert len(history) == 1
    assert history[0].user_query == "What action item was given to Rahul?"


def test_assistant_service_empty_retrieval_fallback(
    memory_db, event_bus, vector_store, embedding_service
):
    """Empty vector retrieval returns factual fallback without LLM call."""
    mock_llm = MockAssistantLLMProvider()
    search_service = SearchService(
        embedding_service=embedding_service,
        vector_store=vector_store,
        db_engine=memory_db,
    )
    retrieval_service = RetrievalService(search_service=search_service)
    service = AssistantService(
        llm=mock_llm,
        retrieval_service=retrieval_service,
    )

    response = service.ask(
        session_id="empty-sess",
        query="What were the Q4 financial results?",
        min_score=0.2,
    )
    assert "does not contain information" in response.answer
    assert response.retrieved_count == 0
    assert response.citations == []
    assert mock_llm.call_count == 0


def test_assistant_service_multi_turn_dialogue(
    memory_db, event_bus, vector_store, embedding_service
):
    """Multi-turn dialogue maintains session conversation memory context."""
    mock_llm = MockAssistantLLMProvider(
        "Based on [Ref 1], Priya is reviewing the UI specs."
    )
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
    retrieval_service = RetrievalService(search_service=search_service)

    with memory_db.session_scope() as session:
        meeting = MeetingRepository.create(session, "UI Sync")
        mid = meeting.id
        t = TranscriptModel(
            meeting_id=mid,
            sequence_number=1,
            timestamp=0.0,
            language="en",
            original_text="Priya is reviewing the frontend UI specs.",
        )
        TranscriptRepository.add(session, t)

    indexer.index_meeting(mid)
    service = AssistantService(
        llm=mock_llm,
        retrieval_service=retrieval_service,
    )

    session_id = "multi-turn-sess"
    # Turn 1
    resp1 = service.ask(session_id, "Who is reviewing UI specs?")
    assert "Priya" in resp1.answer

    # Turn 2 (follow-up question using same session_id)
    resp2 = service.ask(session_id, "When will she complete it?")
    assert resp2 is not None
    assert mock_llm.call_count == 2
    assert len(service.memory.get_history(session_id)) == 2
