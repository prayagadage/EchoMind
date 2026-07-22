"""Repository pattern implementations for Meeting and Transcript persistence."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.storage.models import (
    AlertModel,
    MeetingModel,
    MeetingStatus,
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
