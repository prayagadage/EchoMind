"""Meeting Summarization Engine (Phase 8).

Generates Executive Summaries, Bullet Summaries, and Key Takeaways
using structured meeting context and local LLM inference.
"""

from modules.summary.events import SummaryGeneratedEvent
from modules.summary.models import (
    MeetingSummaryModel,
    SummaryResponseSchema,
    SummaryType,
)
from modules.summary.repository import SummaryRepository
from modules.summary.summary_builder import SummaryBuilder, SummaryContext
from modules.summary.summary_service import SummaryService

__all__ = [
    "MeetingSummaryModel",
    "SummaryBuilder",
    "SummaryContext",
    "SummaryGeneratedEvent",
    "SummaryRepository",
    "SummaryResponseSchema",
    "SummaryService",
    "SummaryType",
]
