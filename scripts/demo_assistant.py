"""Executable demonstration script for Phase 10 AI Meeting Assistant.

Demonstrates Retrieval-Augmented Generation (RAG) over indexed meeting knowledge,
multi-turn conversation memory, anti-hallucination fallbacks, and source citations.
"""

from core.event_bus import EventBus
from core.vector.sqlite_provider import SQLiteVectorStore
from loguru import logger
from modules.assistant.assistant_service import AssistantService
from modules.assistant.conversation_memory import ConversationMemory
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
from modules.summary.models import MeetingSummaryModel, SummaryType
from modules.summary.repository import SummaryRepository


class DemoAssistantLLMProvider:
    """Mock LLM provider returning realistic RAG responses with citations."""

    @property
    def model_id(self) -> str:
        return "demo-qwen3-4b-assistant-v1"

    def generate(
        self,
        prompt: str,
        *,
        system: str = "",
        max_tokens: int = 2048,
    ) -> str:
        prompt_lower = prompt.lower()
        if "action item" in prompt_lower or "rahul" in prompt_lower:
            return (
                "Based on [Ref 1], Rahul was assigned to deploy the staging release "
                "build by Friday, 2026-07-25."
            )
        elif "due" in prompt_lower or "when" in prompt_lower:
            return (
                "According to [Ref 1], Rahul's staging release deployment task is "
                "due on Friday, 2026-07-25."
            )
        elif "risk" in prompt_lower or "token" in prompt_lower:
            return (
                "As noted in [Ref 1], the team identified a token leakage risk on "
                "unencrypted production endpoints."
            )
        else:
            return (
                "According to [Ref 1], the team reviewed the Phase 10 RAG architecture "
                "and aligned on conversational memory."
            )


def run_demo() -> None:
    """Execute AI Meeting Assistant demonstration."""
    logger.info("=" * 60)
    logger.info("EchoMind Phase 10: AI Meeting Assistant (RAG Engine) Demo")
    logger.info("=" * 60)

    # 1. Infrastructure setup
    db = DatabaseEngine(db_url="sqlite:///:memory:")
    db.init_db()
    bus = EventBus(max_workers=2)
    vector_store = SQLiteVectorStore(db_url="sqlite:///:memory:")
    embedder = LocalSemanticEmbeddingProvider()

    indexer = KnowledgeIndexer(
        embedding_service=embedder,
        vector_store=vector_store,
        db_engine=db,
        event_bus=bus,
    )
    search_service = SearchService(
        embedding_service=embedder, vector_store=vector_store, db_engine=db
    )
    retrieval_service = RetrievalService(search_service=search_service)
    mock_llm = DemoAssistantLLMProvider()

    assistant = AssistantService(
        llm=mock_llm,
        retrieval_service=retrieval_service,
        memory=ConversationMemory(max_turns=5),
    )

    # 2. Seed Meeting 1: Phase 10 Assistant Design
    with db.session_scope() as session:
        m1 = MeetingRepository.create(session, "Phase 10 Assistant Design")
        m1_id = m1.id

        spk_rahul = SpeakerModel(
            meeting_id=m1_id,
            temporary_name="Speaker A",
            display_name="Rahul",
            color="#4F46E5",
        )
        spk_priya = SpeakerModel(
            meeting_id=m1_id,
            temporary_name="Speaker B",
            display_name="Priya",
            color="#10B981",
        )
        SpeakerRepository.create(session, spk_rahul)
        SpeakerRepository.create(session, spk_priya)

        t1 = TranscriptModel(
            meeting_id=m1_id,
            sequence_number=1,
            timestamp=0.0,
            language="en",
            original_text="Rahul will deploy the staging release build by Friday.",
            speaker_id=spk_rahul.id,
        )
        TranscriptRepository.add(session, t1)

        summary1 = MeetingSummaryModel(
            meeting_id=m1_id,
            summary_type=SummaryType.COMBINED.value,
            executive_summary="Team finalized RAG Conversational Assistant design.",
            key_takeaways='["Multi-turn memory maintains session context"]',
            is_final=1,
        )
        SummaryRepository.create(session, summary1)

        item1 = IntelligenceItemModel(
            meeting_id=m1_id,
            item_type=ItemType.ACTION_ITEM.value,
            content="Deploy staging release build",
            content_hash="h1_deploy_staging",
            assignee="Rahul",
            due_date="2026-07-25",
            source_text="Rahul will deploy the staging release build by Friday.",
        )
        IntelligenceRepository.create(session, item1)

    # 3. Seed Meeting 2: Production Operations Sync
    with db.session_scope() as session:
        m2 = MeetingRepository.create(session, "Production Operations Sync")
        m2_id = m2.id

        spk_prayag = SpeakerModel(
            meeting_id=m2_id,
            temporary_name="Speaker A",
            display_name="Prayag",
            color="#F59E0B",
        )
        SpeakerRepository.create(session, spk_prayag)

        item2 = IntelligenceItemModel(
            meeting_id=m2_id,
            item_type=ItemType.RISK.value,
            content="Token leakage risk on unencrypted production endpoints",
            content_hash="h2_token_risk",
            priority="HIGH",
            source_text="token leakage risk on unencrypted production endpoints",
        )
        IntelligenceRepository.create(session, item2)

    # Index both meetings
    indexer.index_meeting(m1_id)
    indexer.index_meeting(m2_id)

    logger.info(f"\nIndexed Knowledge Vectors: {vector_store.count()} items.")

    # 4. Multi-Turn RAG Conversation
    session_id = "user-session-99"
    logger.info(f"\n1. Starting Multi-Turn RAG Session [ID: {session_id}]:")

    turns = [
        "What action items were assigned to Rahul?",
        "When are his tasks due?",
        "What security risks were found in production?",
        "What are our financial budget projections for 2030?",
    ]

    for idx, query in enumerate(turns, 1):
        logger.info(f"\n   [Turn {idx}] User: '{query}'")
        resp = assistant.ask(session_id=session_id, query=query, min_score=0.2)
        logger.info(f"   [Turn {idx}] Assistant: {resp.answer}")

        if resp.citations:
            logger.info("   Citations / Source References:")
            for c in resp.citations:
                spk = f" ({c.speaker_name})" if c.speaker_name else ""
                logger.info(
                    f"     • [{c.ref_id}] Meeting: '{c.meeting_title}' | "
                    f"Type: {c.entity_type}{spk}"
                )
                logger.info(f"       Snippet: {c.content_snippet[:65]}...")
        else:
            logger.info("   Citations: None (Factual Fallback / Anti-Hallucination)")

    # 5. Display Conversation History Buffer
    history = assistant.memory.get_history(session_id)
    logger.info(f"\n2. Conversation Memory Buffer ({len(history)} turns retained):")
    for t in history:
        logger.info(f"   User: {t.user_query}")
        logger.info(f"   Assistant: {t.assistant_answer[:60]}...\n")

    bus.shutdown()
    db.close()

    logger.info("=" * 60)
    logger.info("Phase 10 Demo completed successfully!")
    logger.info("=" * 60)


if __name__ == "__main__":
    run_demo()
