"""Unit tests for Phase 5 Real-Time Intelligence & Alert System."""

import time
from unittest.mock import MagicMock

import pytest
from core.event_bus import EventBus
from modules.intelligence.alert_manager import AlertEvent, AlertManager
from modules.intelligence.keyword_matcher import KeywordMatcher
from modules.intelligence.notification_service import NotificationService
from modules.intelligence.rule_engine import Rule, RuleEngine, Severity
from modules.storage.db import DatabaseEngine
from modules.storage.models import AlertModel
from modules.storage.repositories import AlertRepository
from modules.stt.transcript_event import LANG_ENGLISH, TranscriptEvent


@pytest.fixture
def memory_db() -> DatabaseEngine:
    """Provide in-memory DatabaseEngine instance."""
    engine = DatabaseEngine(db_url="sqlite:///:memory:")
    engine.init_db()
    return engine


def test_keyword_matcher_multilingual_triggers() -> None:
    """Verify KeywordMatcher detects English and Devnagari script trigger keywords."""
    matcher = KeywordMatcher(triggers={"Prayag", "प्रयाग", "Deadline", "Urgent"})

    # English trigger
    matches_en = matcher.match("Prayag said the deadline is tomorrow.")
    assert len(matches_en) == 2
    keywords_found = {m.keyword for m in matches_en}
    assert "Prayag" in keywords_found
    assert "Deadline" in keywords_found

    # Devnagari trigger
    matches_mr = matcher.match("आजची मीटिंग प्रयाग घेणार आहे.")
    assert len(matches_mr) == 1
    assert matches_mr[0].keyword == "प्रयाग"


def test_keyword_matcher_highlight() -> None:
    """Verify KeywordMatcher highlights matching keywords."""
    matcher = KeywordMatcher(triggers={"Prayag", "Urgent"})
    highlighted = matcher.highlight("This is an Urgent task for Prayag.")
    assert "**[URGENT]**" in highlighted
    assert "**[PRAYAG]**" in highlighted


def test_rule_engine_evaluation() -> None:
    """Verify RuleEngine evaluates rules and returns matching pairs."""
    rule_urgency = Rule(
        id="r-1",
        name="Urgency Check",
        description="Detect urgent tasks",
        severity=Severity.HIGH,
        keywords={"Urgent"},
    )
    engine = RuleEngine(rules=[rule_urgency])

    results = engine.evaluate("This task is Urgent!")
    assert len(results) == 1
    rule, match = results[0]
    assert rule.id == "r-1"
    assert match.keyword == "Urgent"


def test_notification_service_non_blocking() -> None:
    """Verify NotificationService executes non-blocking banner & sound alerts."""
    service = NotificationService(play_sound_enabled=False)
    # Should not raise exception
    service.notify(title="Test Alert", message="Urgent action required.")


def test_alert_repository_crud(memory_db: DatabaseEngine) -> None:
    """Verify AlertRepository persistence and retrieval."""
    from modules.storage.repositories import MeetingRepository

    with memory_db.session_scope() as session:
        m = MeetingRepository.create(session, "Alert Test Meeting")
        m_id = m.id

        alert = AlertModel(
            meeting_id=m_id,
            rule_name="Name Mention",
            trigger_keyword="Prayag",
            severity="HIGH",
            matched_text="Prayag is presenting.",
        )
        AlertRepository.create(session, alert)

    with memory_db.session_scope() as session:
        alerts = AlertRepository.get_by_meeting(session, m_id)
        assert len(alerts) == 1
        assert alerts[0].trigger_keyword == "Prayag"
        assert alerts[0].severity == "HIGH"


def test_alert_manager_worker_event_bus(memory_db: DatabaseEngine) -> None:
    """Verify AlertManager consumes TranscriptEvent and emits AlertEvent."""
    bus = EventBus(max_workers=2)
    mock_notifier = MagicMock()

    manager = AlertManager(
        event_bus=bus,
        notification_service=mock_notifier,
        db_engine=memory_db,
    )
    manager.start()

    emitted_alerts: list[AlertEvent] = []

    def on_alert(evt: AlertEvent) -> None:
        emitted_alerts.append(evt)

    bus.subscribe(AlertEvent, on_alert)

    # Emit TranscriptEvent with trigger keyword 'Production'
    event = TranscriptEvent(
        text="Deploying new build to Production now.",
        language=LANG_ENGLISH,
        start_time=100.0,
        end_time=102.0,
        confidence=0.98,
        is_final=True,
        sequence_number=1,
    )
    bus.publish(event)

    time.sleep(0.3)
    manager.stop()
    bus.shutdown()

    assert len(emitted_alerts) == 1
    assert emitted_alerts[0].trigger_keyword == "Production"
    assert emitted_alerts[0].severity == "CRITICAL"
    mock_notifier.notify.assert_called_once()
