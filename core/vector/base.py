"""Vector storage interface protocol and data models.

Abstracts local vector storage providers (SQLite, in-memory, or external)
from domain search logic.
"""

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class VectorRecord:
    """Dataclass representing a stored document embedding vector."""

    id: str
    vector: list[float]
    content: str
    entity_type: str
    meeting_id: str
    source_id: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class VectorSearchHit:
    """Dataclass representing a matched vector search result with similarity score."""

    record: VectorRecord
    score: float


@runtime_checkable
class VectorStore(Protocol):
    """Protocol interface for vector storage providers."""

    def add_records(self, records: list[VectorRecord]) -> None:
        """Add or update vector records in the store.

        Args:
            records: List of VectorRecord objects to insert.
        """
        ...

    def search(
        self,
        query_vector: list[float],
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[VectorSearchHit]:
        """Search vector store by similarity to query_vector.

        Args:
            query_vector: Query embedding vector.
            top_k: Maximum number of search hits to return.
            filters: Optional metadata filters (e.g. meeting_id, entity_type).

        Returns:
            list[VectorSearchHit]: Ranked list of search hits sorted by score desc.
        """
        ...

    def delete_by_meeting(self, meeting_id: str) -> int:
        """Delete all vector records associated with a meeting session.

        Args:
            meeting_id: Target meeting UUID string.

        Returns:
            int: Count of deleted vector records.
        """
        ...

    def count(self) -> int:
        """Return total number of vectors in the store.

        Returns:
            int: Vector count.
        """
        ...
