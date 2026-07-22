"""SpeakerIdentityService managing user-driven speaker rename and color assignment."""

import time

from core.event_bus import EventBus
from core.exceptions import EchoMindBaseException
from loguru import logger

from modules.speaker.speaker_events import SpeakerUpdatedEvent
from modules.storage.db import DatabaseEngine
from modules.storage.models import SpeakerModel
from modules.storage.repositories import SpeakerRepository


class SpeakerNotFoundError(EchoMindBaseException):
    """Raised when requested speaker ID is not found in database."""

    pass


class SpeakerIdentityService:
    """Service handling user rename, recolor, and identity queries for speakers."""

    def __init__(
        self,
        db_engine: DatabaseEngine,
        event_bus: EventBus | None = None,
    ) -> None:
        """Initialize SpeakerIdentityService.

        Args:
            db_engine: DatabaseEngine instance.
            event_bus: Optional EventBus for event publishing.
        """
        self._db_engine = db_engine
        self._event_bus = event_bus

    def rename_speaker(
        self, meeting_id: str, speaker_id: str, display_name: str
    ) -> SpeakerModel:
        """Rename a speaker with a custom user display name.

        Args:
            meeting_id: Target meeting UUID string.
            speaker_id: Target speaker UUID string.
            display_name: New human-readable display name.

        Returns:
            SpeakerModel: Updated speaker entity.

        Raises:
            SpeakerNotFoundError: If speaker ID does not exist in meeting.
        """
        clean_name = display_name.strip() if display_name else None

        with self._db_engine.session_scope() as session:
            speaker = SpeakerRepository.get_by_id(session, speaker_id)
            if not speaker or speaker.meeting_id != meeting_id:
                raise SpeakerNotFoundError(
                    f"Speaker '{speaker_id}' not found in meeting '{meeting_id}'"
                )

            speaker.display_name = clean_name
            session.flush()
            temp_name = speaker.temporary_name
            color = speaker.color
            updated_speaker = SpeakerModel(
                id=speaker.id,
                meeting_id=speaker.meeting_id,
                temporary_name=speaker.temporary_name,
                display_name=speaker.display_name,
                color=speaker.color,
                created_at=speaker.created_at,
                last_seen=speaker.last_seen,
            )

        logger.info(
            f"Renamed Speaker '{temp_name}' ({speaker_id[:8]}) -> '{clean_name}'"
        )

        if self._event_bus:
            evt = SpeakerUpdatedEvent(
                speaker_id=speaker_id,
                meeting_id=meeting_id,
                temporary_name=temp_name,
                display_name=clean_name,
                color=color,
                timestamp=time.time(),
            )
            self._event_bus.publish(evt)

        return updated_speaker

    def set_speaker_color(
        self, meeting_id: str, speaker_id: str, color: str
    ) -> SpeakerModel:
        """Assign a custom hex color code to a speaker.

        Args:
            meeting_id: Target meeting UUID string.
            speaker_id: Target speaker UUID string.
            color: Hex color string (e.g. '#10B981').

        Returns:
            SpeakerModel: Updated speaker entity.

        Raises:
            SpeakerNotFoundError: If speaker ID does not exist.
        """
        clean_color = color.strip()

        with self._db_engine.session_scope() as session:
            speaker = SpeakerRepository.get_by_id(session, speaker_id)
            if not speaker or speaker.meeting_id != meeting_id:
                raise SpeakerNotFoundError(
                    f"Speaker '{speaker_id}' not found in meeting '{meeting_id}'"
                )

            speaker.color = clean_color
            session.flush()
            temp_name = speaker.temporary_name
            disp_name = speaker.display_name
            updated_speaker = SpeakerModel(
                id=speaker.id,
                meeting_id=speaker.meeting_id,
                temporary_name=speaker.temporary_name,
                display_name=speaker.display_name,
                color=speaker.color,
                created_at=speaker.created_at,
                last_seen=speaker.last_seen,
            )

        logger.info(f"Set color for Speaker '{speaker_id[:8]}' -> {clean_color}")

        if self._event_bus:
            evt = SpeakerUpdatedEvent(
                speaker_id=speaker_id,
                meeting_id=meeting_id,
                temporary_name=temp_name,
                display_name=disp_name,
                color=clean_color,
                timestamp=time.time(),
            )
            self._event_bus.publish(evt)

        return updated_speaker

    @staticmethod
    def get_effective_name(speaker: SpeakerModel) -> str:
        """Resolve effective display label for a speaker.

        Args:
            speaker: SpeakerModel instance.

        Returns:
            str: display_name if set and non-empty, otherwise temporary_name.
        """
        if speaker.display_name and speaker.display_name.strip():
            return speaker.display_name.strip()
        return speaker.temporary_name
