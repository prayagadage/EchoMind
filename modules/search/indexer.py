"""KnowledgeIndexer for incremental and bulk meeting knowledge indexing."""

import json
import time

from core.event_bus import EventBus
from core.vector.base import VectorRecord, VectorStore
from loguru import logger

from modules.meeting_intelligence.models import IntelligenceItemModel
from modules.meeting_intelligence.repository import IntelligenceRepository
from modules.search.embedding_service import EmbeddingService
from modules.search.events import IndexUpdatedEvent
from modules.search.models import (
    SearchEntityType,
    VectorEmbeddingModel,
    compute_vector_content_hash,
)
from modules.search.vector_repository import VectorRepository
from modules.storage.db import DatabaseEngine
from modules.storage.models import TranscriptModel
from modules.storage.repositories import TranscriptRepository
from modules.summary.models import MeetingSummaryModel
from modules.summary.repository import SummaryRepository


class KnowledgeIndexer:
    """Indexes meeting transcripts, summaries, and intelligence into vector storage."""

    def __init__(
        self,
        embedding_service: EmbeddingService,
        vector_store: VectorStore,
        db_engine: DatabaseEngine,
        event_bus: EventBus,
    ) -> None:
        """Initialize KnowledgeIndexer.

        Args:
            embedding_service: Embedding model provider.
            vector_store: Vector storage provider implementation.
            db_engine: Database engine instance.
            event_bus: EventBus instance.
        """
        self._embedder = embedding_service
        self._vector_store = vector_store
        self._db = db_engine
        self._bus = event_bus

        # Subscribe to meeting completion / artifact events
        self._bus.subscribe(IndexUpdatedEvent, self._on_index_updated)
        logger.debug("KnowledgeIndexer initialized.")

    def _on_index_updated(self, event: IndexUpdatedEvent) -> None:
        """Log indexing completion event."""
        logger.debug(
            f"Index updated for Meeting {event.meeting_id[:8]} "
            f"({event.indexed_count} items)"
        )

    def index_meeting(self, meeting_id: str) -> int:
        """Index all transcripts, summaries, and intelligence items for a meeting.

        Args:
            meeting_id: Target meeting UUID string.

        Returns:
            int: Number of items indexed.
        """
        indexed_count = 0

        # 1. Index Transcripts (using English translated text when available)
        with self._db.session_scope() as session:
            transcripts = TranscriptRepository.get_by_meeting(session, meeting_id)

        for t in transcripts:
            if self._index_transcript(t):
                indexed_count += 1

        # 2. Index Summaries
        with self._db.session_scope() as session:
            summaries = SummaryRepository.get_by_meeting(session, meeting_id)

        for s in summaries:
            if self._index_summary(s):
                indexed_count += 1

        # 3. Index Intelligence Items
        with self._db.session_scope() as session:
            intel_items = IntelligenceRepository.get_by_meeting(session, meeting_id)

        for item in intel_items:
            if self._index_intelligence_item(item):
                indexed_count += 1

        if indexed_count > 0:
            logger.info(
                f"Indexed {indexed_count} knowledge items for "
                f"Meeting {meeting_id[:8]}"
            )
            self._bus.publish(
                IndexUpdatedEvent(
                    meeting_id=meeting_id,
                    indexed_count=indexed_count,
                    timestamp=time.time(),
                )
            )

        return indexed_count

    def _index_transcript(self, transcript: TranscriptModel) -> bool:
        """Index a single transcript segment using English text.

        Args:
            transcript: TranscriptModel instance.

        Returns:
            bool: True if indexed, False if skipped as duplicate.
        """
        text = (
            transcript.translated_text
            if transcript.translated_text
            else transcript.original_text
        )
        if not text.strip():
            return False

        entity_type = SearchEntityType.TRANSCRIPT.value
        content_hash = compute_vector_content_hash(entity_type, text)

        with self._db.session_scope() as session:
            if VectorRepository.exists_by_hash(
                session, transcript.meeting_id, entity_type, content_hash
            ):
                return False

        vec = self._embedder.embed_text(text)

        with self._db.session_scope() as session:
            model = VectorEmbeddingModel(
                meeting_id=transcript.meeting_id,
                entity_type=entity_type,
                source_id=transcript.id,
                content=text,
                vector_json=json.dumps(vec),
                content_hash=content_hash,
            )
            saved = VectorRepository.create(session, model)
            saved_id = saved.id

        # Sync with VectorStore
        meta = {
            "speaker_id": transcript.speaker_id,
            "timestamp": transcript.timestamp,
            "language": transcript.language,
        }
        rec = VectorRecord(
            id=saved_id,
            vector=vec,
            content=text,
            entity_type=entity_type,
            meeting_id=transcript.meeting_id,
            source_id=transcript.id,
            metadata=meta,
        )
        self._vector_store.add_records([rec])
        return True

    def _index_summary(self, summary: MeetingSummaryModel) -> bool:
        """Index a meeting summary.

        Args:
            summary: MeetingSummaryModel instance.

        Returns:
            bool: True if indexed, False if skipped.
        """
        if not summary.executive_summary.strip():
            return False

        entity_type = SearchEntityType.SUMMARY.value
        text = (
            f"Executive Summary: {summary.executive_summary}\n"
            f"Takeaways: {summary.key_takeaways}"
        )
        content_hash = compute_vector_content_hash(entity_type, text)

        with self._db.session_scope() as session:
            if VectorRepository.exists_by_hash(
                session, summary.meeting_id, entity_type, content_hash
            ):
                return False

        vec = self._embedder.embed_text(text)

        with self._db.session_scope() as session:
            model = VectorEmbeddingModel(
                meeting_id=summary.meeting_id,
                entity_type=entity_type,
                source_id=summary.id,
                content=text,
                vector_json=json.dumps(vec),
                content_hash=content_hash,
            )
            saved = VectorRepository.create(session, model)
            saved_id = saved.id

        rec = VectorRecord(
            id=saved_id,
            vector=vec,
            content=text,
            entity_type=entity_type,
            meeting_id=summary.meeting_id,
            source_id=summary.id,
            metadata={"summary_type": summary.summary_type},
        )
        self._vector_store.add_records([rec])
        return True

    def _index_intelligence_item(self, item: IntelligenceItemModel) -> bool:
        """Index a Phase 7 structured intelligence item (Action Item, Decision, etc).

        Args:
            item: IntelligenceItemModel instance.

        Returns:
            bool: True if indexed, False if skipped.
        """
        if not item.content.strip():
            return False

        entity_type = item.item_type
        text = (
            f"[{item.item_type}] {item.content}"
            + (f" (Assignee: {item.assignee})" if item.assignee else "")
            + (f" (Due: {item.due_date})" if item.due_date else "")
        )
        content_hash = compute_vector_content_hash(entity_type, text)

        with self._db.session_scope() as session:
            if VectorRepository.exists_by_hash(
                session, item.meeting_id, entity_type, content_hash
            ):
                return False

        vec = self._embedder.embed_text(text)

        with self._db.session_scope() as session:
            model = VectorEmbeddingModel(
                meeting_id=item.meeting_id,
                entity_type=entity_type,
                source_id=item.id,
                content=text,
                vector_json=json.dumps(vec),
                content_hash=content_hash,
            )
            saved = VectorRepository.create(session, model)
            saved_id = saved.id

        meta = {
            "assignee": item.assignee,
            "due_date": item.due_date,
            "priority": item.priority,
        }
        rec = VectorRecord(
            id=saved_id,
            vector=vec,
            content=text,
            entity_type=entity_type,
            meeting_id=item.meeting_id,
            source_id=item.id,
            metadata=meta,
        )
        self._vector_store.add_records([rec])
        return True
