"""Repository pattern implementations for Meeting and Transcript persistence."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.storage.models import (
    AlertModel,
    MeetingModel,
    MeetingStatus,
    SpeakerModel,
    TranscriptModel,
    TranslationModel,
)


class MeetingRepository:
    """Repository managing Meeting persistence operations."""

    @staticmethod
    def create(session: Session, title: str) -> MeetingModel:
        """Create and persist a new meeting record.

        Args:
            session: Active SQLAlchemy database session.
            title: Title or subject of the meeting.

        Returns:
            MeetingModel: Persisted meeting entity.
        """
        meeting = MeetingModel(
            title=title,
            status=MeetingStatus.IN_PROGRESS.value,
            started_at=datetime.now(UTC),
        )
        session.add(meeting)
        session.flush()
        return meeting

    @staticmethod
    def get_by_id(session: Session, meeting_id: str) -> MeetingModel | None:
        """Retrieve a meeting record by its unique ID.

        Args:
            session: Active SQLAlchemy database session.
            meeting_id: Unique UUID string identifier.

        Returns:
            Optional[MeetingModel]: Meeting entity or None if not found.
        """
        from sqlalchemy.orm import joinedload

        stmt = (
            select(MeetingModel)
            .where(MeetingModel.id == meeting_id)
            .options(joinedload(MeetingModel.transcripts))
        )
        return session.scalar(stmt)

    @staticmethod
    def list_active(session: Session) -> list[MeetingModel]:
        """List all currently active (IN_PROGRESS) meeting records.

        Args:
            session: Active SQLAlchemy database session.

        Returns:
            list[MeetingModel]: List of active meetings.
        """
        stmt = select(MeetingModel).where(
            MeetingModel.status == MeetingStatus.IN_PROGRESS.value
        )
        return list(session.scalars(stmt).all())

    @staticmethod
    def end_meeting(session: Session, meeting_id: str) -> MeetingModel | None:
        """Mark a meeting session as ENDED and record completion timestamp.

        Args:
            session: Active SQLAlchemy database session.
            meeting_id: Unique meeting UUID string.

        Returns:
            Optional[MeetingModel]: Updated meeting entity or None.
        """
        meeting = MeetingRepository.get_by_id(session, meeting_id)
        if meeting:
            meeting.status = MeetingStatus.ENDED.value
            meeting.ended_at = datetime.now(UTC)
            session.flush()
        return meeting

    @staticmethod
    def get_recent(session: Session, limit: int = 50) -> list[MeetingModel]:
        """Retrieve recent meetings ordered by started_at descending.

        Args:
            session: Active SQLAlchemy database session.
            limit: Maximum records count.

        Returns:
            list[MeetingModel]: List of recent meeting entities.
        """
        stmt = (
            select(MeetingModel).order_by(MeetingModel.started_at.desc()).limit(limit)
        )
        return list(session.scalars(stmt).all())

    @staticmethod
    def delete(session: Session, meeting_id: str) -> bool:
        """Delete a meeting entity by ID.

        Args:
            session: Active database session.
            meeting_id: Target meeting UUID string.

        Returns:
            bool: True if deleted successfully.
        """
        meeting = MeetingRepository.get_by_id(session, meeting_id)
        if meeting:
            session.delete(meeting)
            session.flush()
            return True
        return False


class TranscriptRepository:
    """Repository managing Transcript persistence and search operations."""

    @staticmethod
    def add(session: Session, transcript: TranscriptModel) -> TranscriptModel:
        """Persist a new transcript segment.

        Args:
            session: Active SQLAlchemy database session.
            transcript: TranscriptModel instance to save.

        Returns:
            TranscriptModel: Saved transcript entity.
        """
        session.add(transcript)
        session.flush()
        return transcript

    @staticmethod
    def get_by_meeting(session: Session, meeting_id: str) -> list[TranscriptModel]:
        """Retrieve all transcript segments for a given meeting ordered by sequence.

        Args:
            session: Active SQLAlchemy database session.
            meeting_id: Target meeting UUID string.

        Returns:
            list[TranscriptModel]: Ordered list of transcript segments.
        """
        stmt = (
            select(TranscriptModel)
            .where(TranscriptModel.meeting_id == meeting_id)
            .order_by(TranscriptModel.sequence_number)
        )
        return list(session.scalars(stmt).all())

    @staticmethod
    def search_by_keyword(
        session: Session,
        query: str,
        meeting_id: str | None = None,
    ) -> list[TranscriptModel]:
        """Perform full-text search across saved transcripts by keyword.

        Args:
            session: Active SQLAlchemy database session.
            query: Keyword search string.
            meeting_id: Optional filter for a specific meeting session.

        Returns:
            list[TranscriptModel]: Matching transcript segments.
        """
        stmt = select(TranscriptModel).where(
            TranscriptModel.original_text.ilike(f"%{query}%")
        )
        if meeting_id:
            stmt = stmt.where(TranscriptModel.meeting_id == meeting_id)
        stmt = stmt.order_by(TranscriptModel.timestamp)
        return list(session.scalars(stmt).all())

    @staticmethod
    def update_speaker_id(
        session: Session, transcript_id: str, speaker_id: str
    ) -> None:
        """Associate a transcript record with a specific speaker ID.

        Args:
            session: Active database session.
            transcript_id: Target transcript UUID string.
            speaker_id: Target speaker UUID string.
        """
        stmt = select(TranscriptModel).where(TranscriptModel.id == transcript_id)
        transcript = session.scalar(stmt)
        if transcript:
            transcript.speaker_id = speaker_id
            session.flush()


class TranslationRepository:
    """Repository managing Translation persistence and retrieval operations."""

    @staticmethod
    def create(session: Session, translation: TranslationModel) -> TranslationModel:
        """Persist a new translation record.

        Args:
            session: Active SQLAlchemy database session.
            translation: TranslationModel instance to save.

        Returns:
            TranslationModel: Saved translation entity.
        """
        session.add(translation)
        session.flush()
        return translation

    @staticmethod
    def get_by_transcript_id(
        session: Session, transcript_id: str
    ) -> TranslationModel | None:
        """Retrieve translation record for a specific transcript ID.

        Args:
            session: Active SQLAlchemy database session.
            transcript_id: Target transcript UUID string.

        Returns:
            Optional[TranslationModel]: Translation entity or None.
        """
        stmt = select(TranslationModel).where(
            TranslationModel.transcript_id == transcript_id
        )
        return session.scalar(stmt)


class AlertRepository:
    """Repository managing Alert event persistence and retrieval operations."""

    @staticmethod
    def create(session: Session, alert: AlertModel) -> AlertModel:
        """Persist a new alert event record.

        Args:
            session: Active SQLAlchemy database session.
            alert: AlertModel instance to save.

        Returns:
            AlertModel: Saved alert entity.
        """
        session.add(alert)
        session.flush()
        return alert

    @staticmethod
    def get_by_meeting(session: Session, meeting_id: str) -> list[AlertModel]:
        """Retrieve all alert records for a target meeting session.

        Args:
            session: Active SQLAlchemy database session.
            meeting_id: Target meeting UUID string.

        Returns:
            list[AlertModel]: Matching alert records.
        """
        stmt = (
            select(AlertModel)
            .where(AlertModel.meeting_id == meeting_id)
            .order_by(AlertModel.created_at)
        )
        return list(session.scalars(stmt).all())


class SpeakerRepository:
    """Repository managing Speaker entity persistence and retrieval operations."""

    @staticmethod
    def create(session: Session, speaker: SpeakerModel) -> SpeakerModel:
        """Persist a new speaker record.

        Args:
            session: Active SQLAlchemy database session.
            speaker: SpeakerModel instance to save.

        Returns:
            SpeakerModel: Saved speaker entity.
        """
        session.add(speaker)
        session.flush()
        return speaker

    @staticmethod
    def get_by_id(session: Session, speaker_id: str) -> SpeakerModel | None:
        """Retrieve speaker by ID.

        Args:
            session: Active database session.
            speaker_id: Target speaker UUID string.

        Returns:
            SpeakerModel | None: Speaker entity or None.
        """
        stmt = select(SpeakerModel).where(SpeakerModel.id == speaker_id)
        return session.scalar(stmt)

    @staticmethod
    def get_by_meeting(session: Session, meeting_id: str) -> list[SpeakerModel]:
        """Retrieve all speakers associated with a meeting session.

        Args:
            session: Active database session.
            meeting_id: Target meeting UUID string.

        Returns:
            list[SpeakerModel]: List of speakers in the meeting.
        """
        stmt = (
            select(SpeakerModel)
            .where(SpeakerModel.meeting_id == meeting_id)
            .order_by(SpeakerModel.created_at)
        )
        return list(session.scalars(stmt).all())

    @staticmethod
    def update_last_seen(
        session: Session, speaker_id: str, last_seen: datetime
    ) -> None:
        """Update last_seen timestamp for a target speaker.

        Args:
            session: Active database session.
            speaker_id: Target speaker UUID string.
            last_seen: New UTC timestamp.
        """
        speaker = session.scalar(
            select(SpeakerModel).where(SpeakerModel.id == speaker_id)
        )
        if speaker:
            speaker.last_seen = last_seen
            session.flush()

    @staticmethod
    def rename(
        session: Session, speaker_id: str, display_name: str
    ) -> SpeakerModel | None:
        """Update display name for a speaker.

        Args:
            session: Active database session.
            speaker_id: Target speaker UUID string.
            display_name: New human-readable display name.

        Returns:
            SpeakerModel | None: Updated speaker entity or None.
        """
        speaker = session.scalar(
            select(SpeakerModel).where(SpeakerModel.id == speaker_id)
        )
        if speaker:
            speaker.display_name = display_name
            session.flush()
        return speaker

    @staticmethod
    def update_color(
        session: Session, speaker_id: str, color: str
    ) -> SpeakerModel | None:
        """Update color code for a speaker.

        Args:
            session: Active database session.
            speaker_id: Target speaker UUID string.
            color: Hex color string (e.g. #4F46E5).

        Returns:
            SpeakerModel | None: Updated speaker entity or None.
        """
        speaker = session.scalar(
            select(SpeakerModel).where(SpeakerModel.id == speaker_id)
        )
        if speaker:
            speaker.color = color
            session.flush()
        return speaker

    @staticmethod
    def delete(session: Session, speaker_id: str) -> bool:
        """Delete speaker record by ID.

        Args:
            session: Active database session.
            speaker_id: Target speaker UUID string.

        Returns:
            bool: True if deleted, False if not found.
        """
        speaker = session.scalar(
            select(SpeakerModel).where(SpeakerModel.id == speaker_id)
        )
        if speaker:
            session.delete(speaker)
            session.flush()
            return True
        return False

    @staticmethod
    def reassign_transcripts(
        session: Session, target_speaker_id: str, destination_speaker_id: str
    ) -> int:
        """Atomically reassign all transcripts to destination speaker.

        Args:
            session: Active database session.
            target_speaker_id: Speaker ID being merged away.
            destination_speaker_id: Target speaker receiving transcripts.

        Returns:
            int: Number of updated transcript records.
        """
        from sqlalchemy import update

        stmt = (
            update(TranscriptModel)
            .where(TranscriptModel.speaker_id == target_speaker_id)
            .values(speaker_id=destination_speaker_id)
        )
        result = session.execute(stmt)
        session.flush()
        row_count = getattr(result, "rowcount", 0)
        return int(row_count if row_count is not None else 0)
