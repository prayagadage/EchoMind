"""TranslationService independent worker handling transcript translation and events."""

import threading
import time

from core.event_bus import EventBus
from loguru import logger

from modules.storage.db import DatabaseEngine
from modules.storage.models import TranslationModel
from modules.storage.repositories import TranslationRepository
from modules.stt.transcript_event import TranscriptEvent
from modules.translation.engine import TranslationEngine
from modules.translation.translation_event import TranslationEvent


class TranslationService:
    """Independent worker consuming TranscriptEvents and emitting TranslationEvents."""

    def __init__(
        self,
        event_bus: EventBus | None = None,
        translation_engine: TranslationEngine | None = None,
        db_engine: DatabaseEngine | None = None,
        target_language: str = "en",
    ) -> None:
        """Initialize TranslationService instance.

        Args:
            event_bus: EventBus for subscribing and emitting events.
            translation_engine: TranslationEngine instance.
            db_engine: DatabaseEngine instance for TranslationModel persistence.
            target_language: Target output language ISO code (default 'en').
        """
        self._event_bus = event_bus or EventBus()
        self._engine = translation_engine or TranslationEngine(
            default_target_language=target_language
        )
        self._db_engine = db_engine or DatabaseEngine()
        self._target_language = target_language
        self._running = False
        self._lock = threading.Lock()

        logger.debug("TranslationService initialized.")

    def start(self) -> None:
        """Start TranslationService worker by subscribing to TranscriptEvent."""
        with self._lock:
            if self._running:
                return
            self._event_bus.subscribe(TranscriptEvent, self.on_transcript_event)
            self._running = True
            logger.info("TranslationService STARTED & subscribed to TranscriptEvent.")

    def stop(self) -> None:
        """Stop TranslationService worker by unsubscribing from TranscriptEvent."""
        with self._lock:
            if not self._running:
                return
            self._event_bus.unsubscribe(TranscriptEvent, self.on_transcript_event)
            self._running = False
            logger.info("TranslationService STOPPED.")

    def on_transcript_event(self, event: TranscriptEvent) -> None:
        """EventBus subscriber callback handling incoming TranscriptEvent payloads.

        Args:
            event: TranscriptEvent payload emitted by STT pipeline.
        """
        if not self._running:
            return

        # Skip translation if input language is already target language
        if event.language.lower() == self._target_language.lower():
            logger.debug(
                f"Transcript #{event.sequence_number} '{event.language}' "
                f"matches '{self._target_language}'; skipping translation worker."
            )
            return

        # Execute local translation
        translated_text, model_name = self._engine.translate(
            text=event.text,
            source_language=event.language,
            target_language=self._target_language,
        )

        # Create TranslationEvent payload
        trans_event = TranslationEvent(
            transcript_id=getattr(event, "id", f"transcript-{event.sequence_number}"),
            meeting_id=getattr(event, "meeting_id", "active-meeting"),
            sequence_number=event.sequence_number,
            source_language=event.language,
            target_language=self._target_language,
            original_text=event.text,
            translated_text=translated_text,
            model_name=model_name,
            timestamp=time.time(),
        )

        src_l = event.language.upper()
        tgt_l = self._target_language.upper()
        logger.info(
            f"Translation #{trans_event.sequence_number:03d} [{src_l}->{tgt_l}]: "
            f"'{translated_text}'"
        )

        # 1. Publish TranslationEvent onto EventBus
        self._event_bus.publish(trans_event)

        # 2. Persist TranslationModel record into database
        self._persist_translation(trans_event)

    def _persist_translation(self, trans_event: TranslationEvent) -> None:
        """Internal helper saving TranslationModel to SQLite database."""
        if not trans_event.transcript_id or len(trans_event.transcript_id) != 36:
            return

        model = TranslationModel(
            transcript_id=trans_event.transcript_id,
            target_language=trans_event.target_language,
            translated_text=trans_event.translated_text,
            model_name=trans_event.model_name,
        )

        try:
            with self._db_engine.session_scope() as session:
                TranslationRepository.create(session, model)
            tid_sub = trans_event.transcript_id[:8]
            logger.debug(f"Persisted Translation record for Transcript {tid_sub}...")
        except Exception as exc:
            logger.error(f"Failed to persist Translation record: {exc}")
