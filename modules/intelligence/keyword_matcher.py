"""Multilingual keyword and script-aware pattern matcher."""

import re
from dataclasses import dataclass

from loguru import logger

# Default trigger keywords required by EchoMind Phase 5 spec
DEFAULT_TRIGGERS: set[str] = {
    "Prayag",
    "प्रायग",
    "प्रयाग",
    "Deadline",
    "Urgent",
    "Production",
}


@dataclass(frozen=True)
class MatchResult:
    """Dataclass encapsulating a keyword match result in transcript text."""

    keyword: str
    matched_text: str
    start_char: int
    end_char: int


class KeywordMatcher:
    """Multilingual script-aware keyword matching engine."""

    def __init__(self, triggers: set[str] | None = None) -> None:
        """Initialize KeywordMatcher instance.

        Args:
            triggers: Set of trigger keywords or None for DEFAULT_TRIGGERS.
        """
        self._triggers: set[str] = set(triggers or DEFAULT_TRIGGERS)
        logger.debug(f"KeywordMatcher initialized with {len(self._triggers)} triggers.")

    @property
    def triggers(self) -> set[str]:
        """Access set of registered trigger keywords."""
        return set(self._triggers)

    def add_trigger(self, keyword: str) -> None:
        """Add a new keyword trigger."""
        if keyword.strip():
            self._triggers.add(keyword.strip())

    def match(self, text: str) -> list[MatchResult]:
        """Find all matching keyword triggers in the input text string.

        Args:
            text: Input text string.

        Returns:
            List[MatchResult]: List of match instances found in text.
        """
        if not text:
            return []

        results: list[MatchResult] = []

        for kw in self._triggers:
            # Case-insensitive word boundary regex search
            pattern = re.compile(re.escape(kw), re.IGNORECASE)
            for m in pattern.finditer(text):
                results.append(
                    MatchResult(
                        keyword=kw,
                        matched_text=m.group(0),
                        start_char=m.start(),
                        end_char=m.end(),
                    )
                )

        return results

    def highlight(self, text: str) -> str:
        """Return text with matching keywords highlighted using bold brackets.

        Args:
            text: Raw input transcript text.

        Returns:
            str: Highlighted text string.
        """
        matches = self.match(text)
        if not matches:
            return text

        output = text
        # Sort matches in reverse character offset order to avoid index drift
        sorted_matches = sorted(matches, key=lambda m: m.start_char, reverse=True)
        for m in sorted_matches:
            output = (
                output[: m.start_char]
                + f"**[{m.matched_text.upper()}]**"
                + output[m.end_char :]
            )

        return output
