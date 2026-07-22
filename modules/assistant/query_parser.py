"""Query parser analyzing user questions for intent and entity filters."""

import re
from dataclasses import dataclass, field

from modules.search.models import SearchEntityType


@dataclass
class ParsedQuery:
    """Parsed query metadata containing raw query text and optional filter criteria."""

    raw_query: str
    target_entity_type: str | None = None
    target_speaker: str | None = None
    keywords: list[str] = field(default_factory=list)


class QueryParser:
    """Parses natural language questions for search optimization."""

    @staticmethod
    def parse(query: str) -> ParsedQuery:
        """Parse natural language query to extract intent and filters.

        Args:
            query: Natural language query string.

        Returns:
            ParsedQuery: Extracted query structure.
        """
        raw = query.strip()
        lower = raw.lower()

        entity_type: str | None = None
        if "action item" in lower or "todo" in lower or "assigned" in lower:
            entity_type = SearchEntityType.ACTION_ITEM.value
        elif "decision" in lower or "agreed" in lower or "decided" in lower:
            entity_type = SearchEntityType.DECISION.value
        elif "risk" in lower or "vulnerability" in lower or "threat" in lower:
            entity_type = SearchEntityType.RISK.value
        elif "summary" in lower or "overview" in lower:
            entity_type = SearchEntityType.SUMMARY.value
        elif "question" in lower or "asked" in lower:
            entity_type = SearchEntityType.QUESTION.value

        keywords = re.findall(r"\w+", lower)

        return ParsedQuery(
            raw_query=raw,
            target_entity_type=entity_type,
            keywords=keywords,
        )
