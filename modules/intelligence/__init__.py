"""Real-Time Intelligence and Alert System module for EchoMind.

Provides RuleEngine evaluation, multilingual KeywordMatcher, NotificationService
(macOS banner & sound alerts), AlertManager worker, and AlertEvent bus streaming.
"""

from modules.intelligence.alert_manager import AlertEvent, AlertManager
from modules.intelligence.keyword_matcher import KeywordMatcher, MatchResult
from modules.intelligence.notification_service import NotificationService
from modules.intelligence.rule_engine import Rule, RuleEngine, Severity

__all__ = [
    "KeywordMatcher",
    "MatchResult",
    "Rule",
    "RuleEngine",
    "Severity",
    "NotificationService",
    "AlertEvent",
    "AlertManager",
]
