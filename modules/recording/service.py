"""RecordingService orchestrating live audio capture, STT, and indexing."""

import threading
import time
from collections.abc import Callable
from datetime import datetime

from app.container import ApplicationContainer
from loguru import logger

from modules.audio.engine import AudioEngine
from modules.storage.repositories import MeetingRepository, TranscriptRepository
from modules.stt.transcript_event import TranscriptEvent
from modules.stt.transcription_pipeline import TranscriptionPipeline


class RecordingService:
    """Orchestrates live meeting recording and database persistence."""

    def __init__(self, container: ApplicationContainer) -> None:
        """Initialize RecordingService.

        Args:
            container: ApplicationContainer instance.
        """
        self._container = container
        self._audio_engine: AudioEngine | None = None
        self._pipeline: TranscriptionPipeline | None = None
        self._active_meeting_id: str | None = None
        self._start_time: float = 0.0
        self._is_recording: bool = False
        self._lock = threading.Lock()
        self._transcript_listeners: list[Callable[[TranscriptEvent], None]] = []

    @property
    def is_recording(self) -> bool:
        """Get active recording status flag."""
        with self._lock:
            return self._is_recording

    @property
    def active_meeting_id(self) -> str | None:
        """Get currently active meeting UUID."""
        with self._lock:
            return self._active_meeting_id

    @property
    def elapsed_seconds(self) -> float:
        """Get elapsed recording duration in seconds."""
        with self._lock:
            if not self._is_recording or self._start_time == 0.0:
                return 0.0
            return time.time() - self._start_time

    def add_transcript_listener(
        self, listener: Callable[[TranscriptEvent], None]
    ) -> None:
        """Add a callback listener for live transcript events."""
        with self._lock:
            if listener not in self._transcript_listeners:
                self._transcript_listeners.append(listener)

    def start_recording(self, meeting_title: str | None = None) -> str:
        """Start a new live meeting recording session.

        Args:
            meeting_title: Optional custom meeting title.

        Returns:
            str: Created meeting UUID string.
        """
        with self._lock:
            if self._is_recording:
                raise RuntimeError("Recording session is already active.")

            title = (
                meeting_title
                or f"Live Meeting - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )

            # 1. Create meeting record in SQLite
            with self._container.db_engine.session_scope() as session:
                meeting = MeetingRepository.create(session, title)
                meeting_id = meeting.id

            self._active_meeting_id = meeting_id
            self._start_time = time.time()

            # 2. Instantiate and start AudioEngine & TranscriptionPipeline
            self._audio_engine = AudioEngine(
                settings=self._container.settings,
                event_bus=self._container.event_bus,
            )
            self._pipeline = TranscriptionPipeline(
                event_bus=self._audio_engine.event_bus
            )

            # 3. Subscribe DB transcript persistence listener
            def _db_transcript_subscriber(event: TranscriptEvent) -> None:
                if not self._active_meeting_id:
                    return
                try:
                    with self._container.db_engine.session_scope() as session:
                        from modules.storage.models import TranscriptModel

                        t_model = TranscriptModel(
                            meeting_id=self._active_meeting_id,
                            sequence_number=event.sequence_number,
                            timestamp=event.start_time,
                            language=event.language,
                            original_text=event.text,
                        )
                        TranscriptRepository.add(session, t_model)
                except Exception as exc:
                    logger.error(f"Failed to persist transcript event to DB: {exc}")

                # Notify GUI listeners
                with self._lock:
                    listeners = list(self._transcript_listeners)
                for cb in listeners:
                    try:
                        cb(event)
                    except Exception as exc:
                        logger.error(f"Error in transcript listener callback: {exc}")

            self._audio_engine.event_bus.subscribe(
                TranscriptEvent, _db_transcript_subscriber
            )

            self._pipeline.start()
            self._audio_engine.start()
            self._is_recording = True

            logger.info(f"RecordingService STARTED session [mid={meeting_id[:8]}]")
            return meeting_id

    def stop_recording(self) -> str | None:
        """Stop current live recording session and trigger summary & indexer passes.

        Returns:
            Optional[str]: ID of completed meeting, or None if not recording.
        """
        with self._lock:
            if not self._is_recording or not self._active_meeting_id:
                return None

            meeting_id = self._active_meeting_id

            # 1. Stop audio engine and pipeline
            if self._audio_engine:
                try:
                    self._audio_engine.stop()
                except Exception as exc:
                    logger.warning(f"Error stopping audio engine: {exc}")
                self._audio_engine = None

            if self._pipeline:
                try:
                    self._pipeline.stop()
                except Exception as exc:
                    logger.warning(f"Error stopping pipeline: {exc}")
                self._pipeline = None

            # 2. Mark meeting as ENDED in DB
            try:
                with self._container.db_engine.session_scope() as session:
                    MeetingRepository.end_meeting(session, meeting_id)
            except Exception as exc:
                logger.error(f"Failed to end meeting in DB: {exc}")

            self._is_recording = False
            self._active_meeting_id = None
            self._start_time = 0.0

        # 3. Post-recording processing (Async trigger summary & vector indexing)
        try:
            logger.info(f"Triggering final summary for meeting '{meeting_id[:8]}'...")
            self._container.summary_service.generate_final_summary(meeting_id)
        except Exception as exc:
            logger.warning(f"Final summary generation deferred: {exc}")

        try:
            logger.info(f"Triggering vector indexing for meeting '{meeting_id[:8]}'...")
            self._container.indexer.index_meeting(meeting_id)
        except Exception as exc:
            logger.warning(f"Vector indexing deferred: {exc}")

        logger.info(f"RecordingService STOPPED session [mid={meeting_id[:8]}]")
        return meeting_id
