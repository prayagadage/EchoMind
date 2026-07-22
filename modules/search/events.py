"""Event dataclasses for the Semantic Search Subsystem."""

from dataclasses import dataclass


@dataclass(frozen=True)
class IndexUpdatedEvent:
    """Emitted when meeting knowledge vectors are updated in the search index."""

    meeting_id: str
    indexed_count: int
    timestamp: float
