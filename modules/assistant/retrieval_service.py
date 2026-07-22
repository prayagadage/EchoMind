"""RetrievalService interfacing with Phase 9 SearchService for RAG context gathering."""

from loguru import logger

from modules.assistant.query_parser import ParsedQuery
from modules.search.models import SearchResult
from modules.search.search_service import SearchService


class RetrievalService:
    """Retrieves relevant meeting context items for RAG query processing."""

    def __init__(self, search_service: SearchService, default_top_k: int = 5) -> None:
        """Initialize RetrievalService.

        Args:
            search_service: Phase 9 SearchService instance.
            default_top_k: Default top-k hits count.
        """
        self._search_service = search_service
        self._top_k = default_top_k
        logger.debug("RetrievalService initialized.")

    def retrieve_context(
        self,
        parsed_query: ParsedQuery,
        meeting_id: str | None = None,
        top_k: int | None = None,
        min_score: float = 0.0,
    ) -> list[SearchResult]:
        """Retrieve relevant search results for a parsed query.

        Args:
            parsed_query: ParsedQuery instance.
            meeting_id: Optional meeting UUID filter scope.
            top_k: Optional top_k override count.
            min_score: Minimum similarity score threshold.

        Returns:
            list[SearchResult]: List of ranked search results.
        """
        limit = top_k or self._top_k
        query_text = parsed_query.raw_query

        # First pass: try with detected entity_type filter if available
        hits: list[SearchResult] = []
        if parsed_query.target_entity_type:
            hits = self._search_service.search(
                query=query_text,
                top_k=limit,
                meeting_id=meeting_id,
                entity_type=parsed_query.target_entity_type,
            )

        # Fallback pass: search across all types if specific pass returned few hits
        if len(hits) < limit:
            general_hits = self._search_service.search(
                query=query_text,
                top_k=limit,
                meeting_id=meeting_id,
            )
            # Combine unique hits
            seen_ids = {h.id for h in hits}
            for gh in general_hits:
                if gh.id not in seen_ids:
                    hits.append(gh)
                    seen_ids.add(gh.id)

        hits.sort(key=lambda x: x.score, reverse=True)
        # Filter out hits below confidence threshold
        filtered_hits = [h for h in hits if h.score >= min_score]
        return filtered_hits[:limit]
