"""Meeting Intelligence Engine — structured extraction from transcripts.

Extracts action items, decisions, deadlines, questions, risks,
and follow-ups using a local LLM provider.
"""

from modules.meeting_intelligence.events import IntelligenceExtractedEvent
from modules.meeting_intelligence.intelligence_service import (
    IntelligenceError,
    IntelligenceService,
)
from modules.meeting_intelligence.models import (
    IntelligenceItemModel,
    IntelligenceResponse,
    ItemType,
    ParsedItem,
)

__all__ = [
    "IntelligenceError",
    "IntelligenceExtractedEvent",
    "IntelligenceItemModel",
    "IntelligenceResponse",
    "IntelligenceService",
    "ItemType",
    "ParsedItem",
]
