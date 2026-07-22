"""Event payloads emitted by the Meeting Intelligence Engine."""

from dataclasses import dataclass


@dataclass(frozen=True)
class IntelligenceExtractedEvent:
    """Emitted after intelligence items are extracted from transcripts."""

    meeting_id: str
    item_count: int
    item_types: list[str]
    is_final: bool
    timestamp: float
