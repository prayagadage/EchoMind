"""Local Semantic Search and Knowledge Base Module (Phase 9).

Indexes transcripts, summaries, and structured meeting intelligence using
normalized vector embeddings and provides fast offline similarity retrieval.
"""

from modules.search.embedding_service import (
    EmbeddingService,
    LocalSemanticEmbeddingProvider,
)
from modules.search.events import IndexUpdatedEvent
from modules.search.indexer import KnowledgeIndexer
from modules.search.models import (
    SearchEntityType,
    SearchResult,
    VectorEmbeddingModel,
)
from modules.search.search_service import SearchService
from modules.search.vector_repository import VectorRepository

__all__ = [
    "EmbeddingService",
    "IndexUpdatedEvent",
    "KnowledgeIndexer",
    "LocalSemanticEmbeddingProvider",
    "SearchEntityType",
    "SearchResult",
    "SearchService",
    "VectorEmbeddingModel",
    "VectorRepository",
]
