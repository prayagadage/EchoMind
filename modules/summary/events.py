"""Event dataclasses for the Meeting Summarization Engine."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SummaryGeneratedEvent:
    """Emitted when a meeting summary is generated or updated."""

    meeting_id: str
    summary_id: str
    summary_type: str
    is_final: bool
    timestamp: float
