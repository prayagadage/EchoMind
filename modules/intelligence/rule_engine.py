"""Rule Engine evaluating transcript events against configurable intelligence rules."""

from dataclasses import dataclass, field
from enum import StrEnum

from loguru import logger

from modules.intelligence.keyword_matcher import KeywordMatcher, MatchResult


class Severity(StrEnum):
    """Alert severity levels."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class Rule:
    """Configurable rule definition for intelligence trigger detection."""

    id: str
    name: str
    description: str
    severity: Severity = Severity.MEDIUM
    enabled: bool = True
    keywords: set[str] = field(default_factory=set)

    def matches(self, text: str) -> list[MatchResult]:
        """Evaluate rule against transcript text.

        Args:
            text: Transcript text string.

        Returns:
            List[MatchResult]: List of matches found.
        """
        if not self.enabled or not text:
            return []
        matcher = KeywordMatcher(triggers=self.keywords)
        return matcher.match(text)


class RuleEngine:
    """Rule Engine orchestrating evaluation of intelligence rules."""

    def __init__(self, rules: list[Rule] | None = None) -> None:
        """Initialize RuleEngine instance.

        Args:
            rules: List of Rule instances or None for default pre-configured rules.
        """
        self._rules: dict[str, Rule] = {}

        if rules:
            for r in rules:
                self.add_rule(r)
        else:
            self._load_default_rules()

        logger.debug(f"RuleEngine initialized with {len(self._rules)} rule(s).")

    def _load_default_rules(self) -> None:
        """Load default EchoMind Phase 5 rules."""
        rule_name_mention = Rule(
            id="rule-name-mention",
            name="Name Mention",
            description="Alerts when the user's name ('Prayag', 'प्रयाग') is spoken.",
            severity=Severity.HIGH,
            keywords={"Prayag", "प्रायग", "प्रयाग"},
        )

        rule_urgent = Rule(
            id="rule-urgency",
            name="Urgent & Deadline Alert",
            description="Alerts when 'Urgent' or 'Deadline' is spoken.",
            severity=Severity.HIGH,
            keywords={"Deadline", "Urgent"},
        )

        rule_production = Rule(
            id="rule-production",
            name="Production Environment Alert",
            description="Alerts when 'Production' is spoken.",
            severity=Severity.CRITICAL,
            keywords={"Production"},
        )

        self.add_rule(rule_name_mention)
        self.add_rule(rule_urgent)
        self.add_rule(rule_production)

    @property
    def rules(self) -> list[Rule]:
        """Access list of registered rules."""
        return list(self._rules.values())

    def add_rule(self, rule: Rule) -> None:
        """Register a new or updated Rule instance."""
        self._rules[rule.id] = rule
        logger.debug(
            f"Added Rule '{rule.name}' (ID: {rule.id}, Severity: {rule.severity.value})"
        )

    def evaluate(self, text: str) -> list[tuple[Rule, MatchResult]]:
        """Evaluate text against all active registered rules.

        Args:
            text: Transcript text string.

        Returns:
            List[Tuple[Rule, MatchResult]]: List of triggered (rule, match) pairs.
        """
        if not text:
            return []

        results: list[tuple[Rule, MatchResult]] = []

        for rule in self._rules.values():
            if not rule.enabled:
                continue

            matches = rule.matches(text)
            for m in matches:
                results.append((rule, m))

        return results
