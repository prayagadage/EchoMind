"""Executable demonstration script for Phase 9 Local Semantic Search & Knowledge Base.

Demonstrates offline 384-dim vector embedding generation, KnowledgeIndexer,
SQLiteVectorStore, and SearchService semantic retrieval with cosine similarity ranking.
"""

import time

from core.event_bus import EventBus
from core.vector.sqlite_provider import SQLiteVectorStore
from loguru import logger
from modules.meeting_intelligence.models import IntelligenceItemModel, ItemType
from modules.meeting_intelligence.repository import IntelligenceRepository
from modules.search.embedding_service import LocalSemanticEmbeddingProvider
from modules.search.events import IndexUpdatedEvent
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


def run_demo() -> None:
    """Execute Local Semantic Search & Knowledge Base demonstration."""
    logger.info("=" * 60)
    logger.info("EchoMind Phase 9: Local Semantic Search & Knowledge Base Demo")
    logger.info("=" * 60)

    # 1. Infrastructure setup
    db = DatabaseEngine(db_url="sqlite:///:memory:")
    db.init_db()
    bus = EventBus(max_workers=2)
    vector_store = SQLiteVectorStore(db_url="sqlite:///:memory:")
    embedder = LocalSemanticEmbeddingProvider()

    index_events: list[IndexUpdatedEvent] = []
    bus.subscribe(IndexUpdatedEvent, lambda e: index_events.append(e))

    indexer = KnowledgeIndexer(
        embedding_service=embedder,
        vector_store=vector_store,
        db_engine=db,
        event_bus=bus,
    )
    search_service = SearchService(
        embedding_service=embedder, vector_store=vector_store, db_engine=db
    )

    # 2. Seed Meeting 1: Phase 9 Architecture Review
    with db.session_scope() as session:
        m1 = MeetingRepository.create(session, "Phase 9 Architecture Review")
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

        t1_1 = TranscriptModel(
            meeting_id=m1_id,
            sequence_number=1,
            timestamp=0.0,
            language="mr",
            original_text="Aapla objective vector search build karne aahe.",
            translated_text="Our objective is to build offline vector search.",
            speaker_id=spk_rahul.id,
        )
        t1_2 = TranscriptModel(
            meeting_id=m1_id,
            sequence_number=2,
            timestamp=5.0,
            language="en",
            original_text="Priya will implement vector store abstraction.",
            speaker_id=spk_priya.id,
        )
        TranscriptRepository.add(session, t1_1)
        TranscriptRepository.add(session, t1_2)

        # Summary for Meeting 1
        s1 = MeetingSummaryModel(
            meeting_id=m1_id,
            summary_type=SummaryType.COMBINED.value,
            executive_summary="Team designed offline vector storage abstraction layer.",
            key_takeaways='["VectorStore protocol enables swapping vector backends"]',
            is_final=1,
        )
        SummaryRepository.create(session, s1)

        # Action Item for Meeting 1
        i1 = IntelligenceItemModel(
            meeting_id=m1_id,
            item_type=ItemType.ACTION_ITEM.value,
            content="Implement vector store abstraction under core/vector",
            content_hash="h1_action_vector",
            assignee="Priya",
            due_date="2026-07-26",
            source_text="Priya will implement vector store abstraction.",
        )
        IntelligenceRepository.create(session, i1)

    # 3. Seed Meeting 2: Security & Authentication Audit
    with db.session_scope() as session:
        m2 = MeetingRepository.create(session, "Security & Authentication Audit")
        m2_id = m2.id

        spk_prayag = SpeakerModel(
            meeting_id=m2_id,
            temporary_name="Speaker A",
            display_name="Prayag",
            color="#F59E0B",
        )
        SpeakerRepository.create(session, spk_prayag)

        t2_1 = TranscriptModel(
            meeting_id=m2_id,
            sequence_number=1,
            timestamp=0.0,
            language="en",
            original_text="We audited API auth endpoints and fixed leakage risks.",
            speaker_id=spk_prayag.id,
        )
        TranscriptRepository.add(session, t2_1)

        i2 = IntelligenceItemModel(
            meeting_id=m2_id,
            item_type=ItemType.RISK.value,
            content="Token leakage risk on unencrypted endpoints",
            content_hash="h2_risk_token",
            priority="HIGH",
            source_text="fixed token leakage risks",
        )
        IntelligenceRepository.create(session, i2)

    logger.info(f"\nSeeded 2 Meetings: '{m1_id[:8]}' and '{m2_id[:8]}'")

    # 4. Index both meetings
    logger.info("\n1. Indexing Knowledge Vectors for both meetings...")
    count_m1 = indexer.index_meeting(m1_id)
    count_m2 = indexer.index_meeting(m2_id)
    logger.info(f"   Indexed Meeting 1: {count_m1} vectors")
    logger.info(f"   Indexed Meeting 2: {count_m2} vectors")
    logger.info(f"   Total Vectors in SQLiteVectorStore: {vector_store.count()}")

    # 5. Execute Natural Language Semantic Searches
    queries = [
        "vector store abstraction",
        "action items assigned to Priya",
        "token leakage security risk",
    ]

    logger.info("\n2. Executing Semantic Searches Across Knowledge Base:")
    for query in queries:
        logger.info(f"\n   🔍 QUERY: '{query}'")
        results = search_service.search(query, top_k=3)
        for idx, r in enumerate(results, 1):
            spk = f" ({r.speaker_name})" if r.speaker_name else ""
            ts = f" [{r.timestamp:.1f}s]" if r.timestamp is not None else ""
            logger.info(
                f"      [{idx}] Score: {r.score:.4f} | Meeting: '{r.meeting_title}' | "
                f"Type: {r.entity_type}{spk}{ts}"
            )
            logger.info(f"          → {r.content[:70]}...")

    # 6. Event verification
    time.sleep(0.3)
    logger.info(f"\n3. Index Events Received on EventBus: {len(index_events)}")
    for evt in index_events:
        m_id = evt.meeting_id[:8]
        logger.info(f"   Event -> Meeting {m_id} indexed ({evt.indexed_count} items)")

    bus.shutdown()
    db.close()

    logger.info("\n" + "=" * 60)
    logger.info("Phase 9 Demo completed successfully!")
    logger.info("=" * 60)


if __name__ == "__main__":
    run_demo()
