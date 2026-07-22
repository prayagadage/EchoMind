"""TranscriptService managing meeting lifecycle, auto-persistence, and search."""

import threading

from core.event_bus import EventBus
from loguru import logger

from modules.storage.db import DatabaseEngine
from modules.storage.models import MeetingModel, TranscriptModel
from modules.storage.repositories import MeetingRepository, TranscriptRepository
from modules.stt.transcript_event import TranscriptEvent


class TranscriptService:
    """High-level service managing persistent memory, meeting lifecycle, and search."""

    def __init__(
        self,
        db_engine: DatabaseEngine | None = None,
        event_bus: EventBus | None = None,
    ) -> None:
        """Initialize TranscriptService instance.

        Args:
            db_engine: DatabaseEngine instance for SQLite session management.
            event_bus: EventBus for subscribing to incoming TranscriptEvent payloads.
        """
        self._db_engine = db_engine or DatabaseEngine()
        self._event_bus = event_bus or EventBus()
        self._active_meeting_id: str | None = None
        self._lock = threading.Lock()

        # Initialize schema tables
        self._db_engine.init_db()

        # Subscribe to TranscriptEvent payloads on EventBus
        self._event_bus.subscribe(TranscriptEvent, self.on_transcript_event)
        logger.debug("TranscriptService initialized & subscribed to TranscriptEvent.")

    @property
    def db_engine(self) -> DatabaseEngine:
        """Access underlying DatabaseEngine instance."""
        return self._db_engine

    @property
    def active_meeting_id(self) -> str | None:
        """Access current active meeting UUID string."""
        with self._lock:
            return self._active_meeting_id

    def start_meeting(self, title: str = "Untitled Meeting") -> MeetingModel:
        """Start a new meeting session and set it as active.

        Args:
            title: Descriptive subject or title of meeting.

        Returns:
            MeetingModel: Created meeting entity.
        """
        with self._db_engine.session_scope() as session:
            meeting = MeetingRepository.create(session, title)
            meeting_id = meeting.id

        with self._lock:
            self._active_meeting_id = meeting_id

        logger.info(f"Started new meeting '{title}' (ID: {meeting_id})")

        # Fetch and return instance within fresh scope
        with self._db_engine.session_scope() as session:
            return MeetingRepository.get_by_id(session, meeting_id)  # type: ignore[return-value]

    def end_meeting(self, meeting_id: str | None = None) -> MeetingModel | None:
        """End an active meeting session.

        Args:
            meeting_id: Specific meeting ID or None for active meeting.

        Returns:
            Optional[MeetingModel]: Updated meeting record.
        """
        target_id = meeting_id or self.active_meeting_id
        if not target_id:
            logger.warning("End meeting requested but no active meeting context found.")
            return None

        with self._db_engine.session_scope() as session:
            updated = MeetingRepository.end_meeting(session, target_id)

        with self._lock:
            if self._active_meeting_id == target_id:
                self._active_meeting_id = None

        logger.info(f"Ended meeting (ID: {target_id}).")
        return updated

    def on_transcript_event(self, event: TranscriptEvent) -> None:
        """EventBus subscriber callback auto-persisting TranscriptEvents.

        Args:
            event: TranscriptEvent emitted by STT pipeline.
        """
        meeting_id = self.active_meeting_id
        if not meeting_id:
            logger.debug(
                f"TranscriptEvent #{event.sequence_number} received but "
                "no active meeting context; skipping storage."
            )
            return

        self.append_transcript(event, meeting_id=meeting_id)

    def append_transcript(
        self,
        event: TranscriptEvent,
        meeting_id: str | None = None,
    ) -> TranscriptModel | None:
        """Explicitly persist a TranscriptEvent for a meeting session.

        Args:
            event: TranscriptEvent payload.
            meeting_id: Target meeting UUID or None for active meeting.

        Returns:
            Optional[TranscriptModel]: Persisted transcript model or None.
        """
        target_id = meeting_id or self.active_meeting_id
        if not target_id:
            logger.warning("Cannot append transcript: no meeting ID specified.")
            return None

        model = TranscriptModel(
            meeting_id=target_id,
            sequence_number=event.sequence_number,
            timestamp=event.start_time,
            language=event.language,
            original_text=event.text,
            confidence=event.confidence,
        )

        with self._db_engine.session_scope() as session:
            saved = TranscriptRepository.add(session, model)
            saved_id = saved.id

        logger.debug(
            f"Stored Transcript #{event.sequence_number} for Meeting {target_id[:8]}..."
        )

        with self._db_engine.session_scope() as session:
            return session.get(TranscriptModel, saved_id)

    def get_meeting(self, meeting_id: str) -> MeetingModel | None:
        """Retrieve meeting record including transcript history.

        Args:
            meeting_id: Unique meeting UUID string.

        Returns:
            Optional[MeetingModel]: Meeting entity or None.
        """
        with self._db_engine.session_scope() as session:
            return MeetingRepository.get_by_id(session, meeting_id)

    def search_transcripts(
        self, query: str, meeting_id: str | None = None
    ) -> list[TranscriptModel]:
        """Perform full-text search across stored transcript segments.

        Args:
            query: Search keyword string.
            meeting_id: Optional meeting ID filter.

        Returns:
            list[TranscriptModel]: Matching transcript segments.
        """
        with self._db_engine.session_scope() as session:
            return TranscriptRepository.search_by_keyword(session, query, meeting_id)
