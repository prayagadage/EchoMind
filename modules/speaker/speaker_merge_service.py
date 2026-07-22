"""SpeakerMergeService handling safe speaker merging and transcript re-linking."""

import time

from core.event_bus import EventBus
from core.exceptions import EchoMindBaseException
from loguru import logger

from modules.speaker.speaker_events import SpeakerMergedEvent
from modules.storage.db import DatabaseEngine
from modules.storage.repositories import SpeakerRepository


class SpeakerMergeError(EchoMindBaseException):
    """Raised when speaker merge operation encounters invalid state."""

    pass


class SpeakerMergeService:
    """Service executing safe speaker merging operations."""

    def __init__(
        self,
        db_engine: DatabaseEngine,
        event_bus: EventBus | None = None,
    ) -> None:
        """Initialize SpeakerMergeService.

        Args:
            db_engine: DatabaseEngine instance.
            event_bus: Optional EventBus for event publishing.
        """
        self._db_engine = db_engine
        self._event_bus = event_bus

    def merge_speakers(
        self,
        meeting_id: str,
        target_speaker_id: str,
        destination_speaker_id: str,
    ) -> int:
        """Merge target_speaker into destination_speaker.

        All transcripts referencing target_speaker_id will be updated to point to
        destination_speaker_id. The target speaker's last_seen is merged into
        destination speaker, and the target speaker record is safely deleted.

        Args:
            meeting_id: Target meeting UUID string.
            target_speaker_id: Speaker ID being merged away (Speaker C).
            destination_speaker_id: Target speaker receiving transcripts (Speaker A).

        Returns:
            int: Number of transcript segments updated.

        Raises:
            SpeakerMergeError: If target/destination missing or IDs identical.
        """
        if target_speaker_id == destination_speaker_id:
            raise SpeakerMergeError(
                "Target speaker ID and destination speaker ID cannot be identical."
            )

        with self._db_engine.session_scope() as session:
            target_spk = SpeakerRepository.get_by_id(session, target_speaker_id)
            dest_spk = SpeakerRepository.get_by_id(session, destination_speaker_id)

            if not target_spk or target_spk.meeting_id != meeting_id:
                t_id = target_speaker_id
                raise SpeakerMergeError(
                    f"Target speaker '{t_id}' not found in meeting '{meeting_id}'"
                )
            if not dest_spk or dest_spk.meeting_id != meeting_id:
                d_id = destination_speaker_id
                raise SpeakerMergeError(
                    f"Destination speaker '{d_id}' not found in meeting '{meeting_id}'"
                )

            target_temp = target_spk.temporary_name
            dest_temp = dest_spk.temporary_name

            # 1. Update last_seen timestamp on destination speaker
            if target_spk.last_seen > dest_spk.last_seen:
                dest_spk.last_seen = target_spk.last_seen

            # 2. Re-link all transcript records in SQLite
            affected_count = SpeakerRepository.reassign_transcripts(
                session, target_speaker_id, destination_speaker_id
            )

            # 3. Delete target speaker record
            SpeakerRepository.delete(session, target_speaker_id)
            session.flush()

        logger.info(
            f"Merged Speaker '{target_temp}' ({target_speaker_id[:8]}) into "
            f"'{dest_temp}' ({destination_speaker_id[:8]}). "
            f"Reassigned {affected_count} transcript segments."
        )

        if self._event_bus:
            evt = SpeakerMergedEvent(
                meeting_id=meeting_id,
                target_speaker_id=target_speaker_id,
                destination_speaker_id=destination_speaker_id,
                affected_transcripts_count=affected_count,
                timestamp=time.time(),
            )
            self._event_bus.publish(evt)

        return affected_count
