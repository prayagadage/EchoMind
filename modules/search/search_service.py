"""SearchService orchestrating semantic retrieval and result ranking."""

from core.exceptions import SearchError
from core.vector.base import VectorStore
from loguru import logger

from modules.search.embedding_service import EmbeddingService
from modules.search.models import SearchResult
from modules.storage.db import DatabaseEngine
from modules.storage.repositories import MeetingRepository, SpeakerRepository


class SearchService:
    """High-level semantic search service for meeting knowledge base retrieval."""

    def __init__(
        self,
        embedding_service: EmbeddingService,
        vector_store: VectorStore,
        db_engine: DatabaseEngine,
    ) -> None:
        """Initialize SearchService.

        Args:
            embedding_service: Embedding model provider implementation.
            vector_store: Vector storage provider implementation.
            db_engine: Database engine instance for metadata enrichment.
        """
        self._embedder = embedding_service
        self._vector_store = vector_store
        self._db = db_engine
        logger.debug("SearchService initialized.")

    def search(
        self,
        query: str,
        top_k: int = 10,
        meeting_id: str | None = None,
        entity_type: str | None = None,
    ) -> list[SearchResult]:
        """Perform semantic vector search across meeting knowledge.

        Args:
            query: Natural language query string.
            top_k: Maximum number of ranked search hits to return.
            meeting_id: Optional meeting UUID filter.
            entity_type: Optional SearchEntityType string filter.

        Returns:
            list[SearchResult]: Ranked list of SearchResult objects sorted by score.

        Raises:
            SearchError: If embedding generation or search execution fails.
        """
        if not query.strip():
            return []

        try:
            query_vector = self._embedder.embed_text(query)
        except Exception as exc:
            logger.error(f"Failed to generate query embedding: {exc}")
            raise SearchError(
                message=f"Query embedding generation failed: {exc}",
                details={"query": query},
            ) from exc

        filters: dict[str, str] = {}
        if meeting_id:
            filters["meeting_id"] = meeting_id
        if entity_type:
            filters["entity_type"] = entity_type

        try:
            hits = self._vector_store.search(
                query_vector, top_k=top_k, filters=filters if filters else None
            )
        except Exception as exc:
            logger.error(f"Vector search failed: {exc}")
            raise SearchError(
                message=f"Vector search failed: {exc}",
                details={"query": query},
            ) from exc

        if not hits:
            logger.debug(f"No semantic search hits found for query: '{query}'")
            return []

        results: list[SearchResult] = []

        with self._db.session_scope() as session:
            # Cache meeting titles and speaker names for performance
            meeting_titles: dict[str, str] = {}
            speaker_names: dict[str, str] = {}

            for hit in hits:
                rec = hit.record
                mid = rec.meeting_id

                if mid not in meeting_titles:
                    m = MeetingRepository.get_by_id(session, mid)
                    meeting_titles[mid] = m.title if m else "Untitled Meeting"

                spk_id = rec.metadata.get("speaker_id")
                spk_name: str | None = None
                if spk_id:
                    if spk_id not in speaker_names:
                        spk = SpeakerRepository.get_by_id(session, spk_id)
                        if spk:
                            speaker_names[spk_id] = (
                                spk.display_name or spk.temporary_name
                            )
                    spk_name = speaker_names.get(spk_id)

                ts = rec.metadata.get("timestamp")

                results.append(
                    SearchResult(
                        id=rec.id,
                        meeting_id=mid,
                        meeting_title=meeting_titles[mid],
                        entity_type=rec.entity_type,
                        source_id=rec.source_id,
                        content=rec.content,
                        score=hit.score,
                        speaker_name=spk_name,
                        timestamp=float(ts) if ts is not None else None,
                    )
                )

        logger.info(
            f"Semantic search for '{query}' returned {len(results)} hit(s) "
            f"(top score: {results[0].score:.4f})"
        )
        return results
