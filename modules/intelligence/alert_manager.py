"""AlertManager orchestrator evaluating transcript streams and triggering alerts."""

import threading
import time
from dataclasses import dataclass

from core.event_bus import EventBus
from loguru import logger

from modules.intelligence.keyword_matcher import KeywordMatcher
from modules.intelligence.notification_service import NotificationService
from modules.intelligence.rule_engine import RuleEngine
from modules.storage.db import DatabaseEngine
from modules.storage.models import AlertModel
from modules.storage.repositories import AlertRepository
from modules.stt.transcript_event import TranscriptEvent
from modules.translation.translation_event import TranslationEvent


@dataclass(frozen=True)
class AlertEvent:
    """Immutable payload emitted when an intelligence rule triggers an alert."""

    alert_id: str
    meeting_id: str
    transcript_id: str | None
    rule_name: str
    trigger_keyword: str
    severity: str
    matched_text: str
    highlighted_text: str
    timestamp: float


class AlertManager:
    """Worker consuming TranscriptEvents & TranslationEvents to manage alerts."""

    def __init__(
        self,
        event_bus: EventBus | None = None,
        rule_engine: RuleEngine | None = None,
        notification_service: NotificationService | None = None,
        db_engine: DatabaseEngine | None = None,
    ) -> None:
        """Initialize AlertManager instance.

        Args:
            event_bus: EventBus for subscribing to events and emitting
                AlertEvent.
            rule_engine: RuleEngine instance for condition evaluation.
            notification_service: NotificationService instance.
            db_engine: DatabaseEngine instance for AlertModel persistence.
        """
        self._event_bus = event_bus or EventBus()
        self._rule_engine = rule_engine or RuleEngine()
        self._notification_service = notification_service or NotificationService()
        self._db_engine = db_engine or DatabaseEngine()
        self._keyword_matcher = KeywordMatcher()
        self._running = False
        self._lock = threading.Lock()

        logger.debug("AlertManager initialized.")

    def start(self) -> None:
        """Start AlertManager worker by subscribing to event channels."""
        with self._lock:
            if self._running:
                return
            self._event_bus.subscribe(TranscriptEvent, self.on_transcript_event)
            self._event_bus.subscribe(TranslationEvent, self.on_translation_event)
            self._running = True
            logger.info("AlertManager STARTED & subscribed to event channels.")

    def stop(self) -> None:
        """Stop AlertManager worker by unsubscribing from event channels."""
        with self._lock:
            if not self._running:
                return
            self._event_bus.unsubscribe(TranscriptEvent, self.on_transcript_event)
            self._event_bus.unsubscribe(TranslationEvent, self.on_translation_event)
            self._running = False
            logger.info("AlertManager STOPPED.")

    def on_transcript_event(self, event: TranscriptEvent) -> None:
        """Subscriber handler receiving raw TranscriptEvent payloads.

        Args:
            event: TranscriptEvent payload.
        """
        self._process_text_evaluation(
            text=event.text,
            transcript_id=getattr(event, "id", f"transcript-{event.sequence_number}"),
            meeting_id=getattr(event, "meeting_id", "active-meeting"),
        )

    def on_translation_event(self, event: TranslationEvent) -> None:
        """Subscriber handler receiving translated TranslationEvent payloads.

        Args:
            event: TranslationEvent payload.
        """
        # Also evaluate translated text for English keyword matches
        self._process_text_evaluation(
            text=event.translated_text,
            transcript_id=event.transcript_id,
            meeting_id=event.meeting_id,
        )

    def _process_text_evaluation(
        self, text: str, transcript_id: str | None, meeting_id: str
    ) -> None:
        """Internal helper evaluating text against RuleEngine rules."""
        if not self._running or not text:
            return

        triggered = self._rule_engine.evaluate(text)
        if not triggered:
            return

        for rule, match in triggered:
            highlighted = self._keyword_matcher.highlight(text)

            alert_evt = AlertEvent(
                alert_id=f"alert-{int(time.time()*1000)}",
                meeting_id=meeting_id,
                transcript_id=transcript_id,
                rule_name=rule.name,
                trigger_keyword=match.keyword,
                severity=rule.severity.value,
                matched_text=text,
                highlighted_text=highlighted,
                timestamp=time.time(),
            )

            sev = alert_evt.severity
            logger.warning(
                f"ALERT TRIGGERED [{sev}] '{rule.name}' -> Keyword: '{match.keyword}'"
            )

            # 1. Publish AlertEvent onto EventBus
            self._event_bus.publish(alert_evt)

            # 2. Trigger macOS notification banner & sound alert
            self._notification_service.notify(
                title=f"EchoMind Alert: {rule.name}",
                message=f"Triggered keyword '{match.keyword}' in meeting.",
                subtitle=f"Severity: {rule.severity.value}",
            )

            # 3. Persist AlertModel entry in SQLite
            self._persist_alert(alert_evt)

    def _persist_alert(self, alert_evt: AlertEvent) -> None:
        """Persist AlertModel entity to SQLite database."""
        if not alert_evt.meeting_id or alert_evt.meeting_id == "active-meeting":
            return

        model = AlertModel(
            meeting_id=alert_evt.meeting_id,
            transcript_id=(
                alert_evt.transcript_id
                if alert_evt.transcript_id and len(alert_evt.transcript_id) == 36
                else None
            ),
            rule_name=alert_evt.rule_name,
            trigger_keyword=alert_evt.trigger_keyword,
            severity=alert_evt.severity,
            matched_text=alert_evt.matched_text,
        )

        try:
            with self._db_engine.session_scope() as session:
                AlertRepository.create(session, model)
            logger.debug(f"Persisted Alert record for Rule '{alert_evt.rule_name}'.")
        except Exception as exc:
            logger.error(f"Failed to persist Alert record: {exc}")
