"""SpeakerService independent worker processing audio streams and SpeakerEvents."""

import threading
import time
from datetime import UTC, datetime

from core.event_bus import EventBus
from loguru import logger
from sqlalchemy import select

from modules.audio.models import AudioChunk
from modules.speaker.speaker_events import (
    SpeakerAssignedEvent,
    SpeakerChangedEvent,
    SpeakerEndedEvent,
    SpeakerStartedEvent,
)
from modules.speaker.speaker_segmenter import (
    SpeakerSegmenter,
)
from modules.storage.db import DatabaseEngine
from modules.storage.models import SpeakerModel, TranscriptModel
from modules.storage.repositories import SpeakerRepository
from modules.stt.transcript_event import TranscriptEvent


class SpeakerService:
    """Worker consuming AudioChunks & TranscriptEvents for speaker segmentation."""

    def __init__(
        self,
        event_bus: EventBus | None = None,
        segmenter: SpeakerSegmenter | None = None,
        db_engine: DatabaseEngine | None = None,
    ) -> None:
        """Initialize SpeakerService instance.

        Args:
            event_bus: EventBus for subscribing and publishing events.
            segmenter: SpeakerSegmenter instance.
            db_engine: DatabaseEngine instance for SpeakerModel persistence.
        """
        self._event_bus = event_bus or EventBus()
        self._segmenter = segmenter or SpeakerSegmenter()
        self._db_engine = db_engine or DatabaseEngine()
        self._running = False
        self._lock = threading.Lock()

        # Active meeting session speaker state
        self._current_meeting_id: str | None = None
        self._active_speaker_id: str | None = None
        self._active_temporary_name: str | None = None
        self._speaker_start_time: float = 0.0
        self._meeting_speakers: dict[str, str] = {}  # db_id -> temp_name

        logger.debug("SpeakerService initialized.")

    def start(self) -> None:
        """Start SpeakerService worker by subscribing to EventBus channels."""
        with self._lock:
            if self._running:
                return
            self._event_bus.subscribe(AudioChunk, self.on_audio_chunk)
            self._event_bus.subscribe(TranscriptEvent, self.on_transcript_event)
            self._running = True
            logger.info(
                "SpeakerService STARTED & subscribed to AudioChunk & TranscriptEvent."
            )

    def stop(self) -> None:
        """Stop SpeakerService worker by unsubscribing from EventBus channels."""
        with self._lock:
            if not self._running:
                return
            self._event_bus.unsubscribe(AudioChunk, self.on_audio_chunk)
            self._event_bus.unsubscribe(TranscriptEvent, self.on_transcript_event)
            self._running = False
            logger.info("SpeakerService STOPPED.")

    def set_active_meeting(self, meeting_id: str) -> None:
        """Set active meeting ID for speaker tracking context."""
        with self._lock:
            self._current_meeting_id = meeting_id
            self._segmenter.reset()
            self._active_speaker_id = None
            self._active_temporary_name = None
            self._meeting_speakers.clear()
            logger.info(f"SpeakerService active meeting set to '{meeting_id}'.")

    def on_audio_chunk(self, chunk: AudioChunk) -> None:
        """Process incoming streaming AudioChunk for speaker segmentation.

        Args:
            chunk: AudioChunk payload.
        """
        if not self._running or chunk.data is None:
            return

        now = time.time()
        res = self._segmenter.process_chunk(chunk.data, chunk.sample_rate)

        if res.is_silence:
            return

        with self._lock:
            # 1. Handle Speaker Change event
            if res.is_speaker_change or self._active_speaker_id is None:
                prev_id = self._active_speaker_id
                prev_name = self._active_temporary_name

                # Emit SpeakerEndedEvent if previous speaker was active
                if prev_id and prev_name:
                    dur = max(0.1, now - self._speaker_start_time)
                    ended_evt = SpeakerEndedEvent(
                        speaker_id=prev_id,
                        temporary_name=prev_name,
                        duration=dur,
                        timestamp=now,
                    )
                    self._event_bus.publish(ended_evt)

                # Ensure SpeakerModel is persisted in SQLite
                db_speaker_id = self._ensure_speaker_db_record(
                    res.speaker_id, res.temporary_name
                )

                # Emit SpeakerStartedEvent and SpeakerChangedEvent
                self._active_speaker_id = db_speaker_id
                self._active_temporary_name = res.temporary_name
                self._speaker_start_time = now

                started_evt = SpeakerStartedEvent(
                    speaker_id=db_speaker_id,
                    temporary_name=res.temporary_name,
                    timestamp=now,
                )
                self._event_bus.publish(started_evt)

                changed_evt = SpeakerChangedEvent(
                    previous_speaker_id=prev_id,
                    new_speaker_id=db_speaker_id,
                    new_temporary_name=res.temporary_name,
                    timestamp=now,
                )
                self._event_bus.publish(changed_evt)
            else:
                # Update last_seen timestamp in database
                if self._active_speaker_id:
                    self._update_speaker_last_seen(self._active_speaker_id)

    def on_transcript_event(self, event: TranscriptEvent) -> None:
        """Subscriber handler linking TranscriptEvent segments with active speaker ID.

        Args:
            event: TranscriptEvent payload.
        """
        if not self._running:
            return

        with self._lock:
            spk_id = self._active_speaker_id
            temp_name = self._active_temporary_name or "Speaker A"
            m_id = getattr(
                event, "meeting_id", self._current_meeting_id or "active-meeting"
            )

        if not spk_id:
            # Fallback initial speaker
            spk_id = self._ensure_speaker_db_record("default-speaker", temp_name)
            self._active_speaker_id = spk_id
            self._active_temporary_name = temp_name

        t_id = getattr(event, "id", None)
        seq_num = event.sequence_number

        # 1. Update Transcript record in SQLite
        try:
            with self._db_engine.session_scope() as session:
                transcript = None
                if t_id and len(t_id) == 36:
                    transcript = session.scalar(
                        select(TranscriptModel).where(TranscriptModel.id == t_id)
                    )

                if not transcript and m_id and m_id != "active-meeting":
                    transcript = session.scalar(
                        select(TranscriptModel).where(
                            TranscriptModel.meeting_id == m_id,
                            TranscriptModel.sequence_number == seq_num,
                        )
                    )

                if transcript:
                    transcript.speaker_id = spk_id
                    t_id = transcript.id
                    session.flush()
                    sid_sub = spk_id[:8]
                    logger.debug(
                        f"Linked Transcript #{seq_num} to {temp_name} ({sid_sub})"
                    )
        except Exception as exc:
            logger.error(f"Failed to update transcript speaker_id: {exc}")

        final_t_id = t_id or f"transcript-{seq_num}"

        # 2. Publish SpeakerAssignedEvent onto EventBus
        assigned_evt = SpeakerAssignedEvent(
            transcript_id=final_t_id,
            meeting_id=m_id,
            speaker_id=spk_id,
            temporary_name=temp_name,
            timestamp=time.time(),
        )
        self._event_bus.publish(assigned_evt)

    def _ensure_speaker_db_record(
        self, raw_speaker_id: str, temporary_name: str
    ) -> str:
        """Ensure SpeakerModel entity is persisted in SQLite database."""
        m_id = self._current_meeting_id
        if not m_id or m_id == "active-meeting":
            return raw_speaker_id

        # Return cached DB ID if already created
        if raw_speaker_id in self._meeting_speakers:
            return raw_speaker_id

        try:
            with self._db_engine.session_scope() as session:
                speaker = SpeakerModel(
                    id=raw_speaker_id,
                    meeting_id=m_id,
                    temporary_name=temporary_name,
                )
                SpeakerRepository.create(session, speaker)
                self._meeting_speakers[raw_speaker_id] = temporary_name
                spk_sub = raw_speaker_id[:8]
                logger.info(
                    f"Persisted Speaker '{temporary_name}' ({spk_sub}) into SQLite."
                )
            return raw_speaker_id
        except Exception as exc:
            logger.debug(f"Speaker model creation note: {exc}")
            return raw_speaker_id

    def _update_speaker_last_seen(self, speaker_id: str) -> None:
        """Update last_seen timestamp in database."""
        if not self._current_meeting_id or len(speaker_id) != 36:
            return
        try:
            with self._db_engine.session_scope() as session:
                SpeakerRepository.update_last_seen(
                    session, speaker_id, datetime.now(UTC)
                )
        except Exception as exc:
            logger.debug(f"Failed to update speaker last_seen: {exc}")
