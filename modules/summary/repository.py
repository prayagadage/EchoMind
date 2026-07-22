"""Repository pattern implementation for MeetingSummary persistence."""

import json
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.summary.models import MeetingSummaryModel


class SummaryRepository:
    """Repository managing MeetingSummaryModel database operations."""

    @staticmethod
    def create(session: Session, summary: MeetingSummaryModel) -> MeetingSummaryModel:
        """Persist a new meeting summary record.

        Args:
            session: Active database session.
            summary: MeetingSummaryModel instance.

        Returns:
            MeetingSummaryModel: Persisted entity.
        """
        session.add(summary)
        session.flush()
        return summary

    @staticmethod
    def get_by_meeting(session: Session, meeting_id: str) -> list[MeetingSummaryModel]:
        """Retrieve all summary records for a target meeting.

        Args:
            session: Active database session.
            meeting_id: Target meeting UUID string.

        Returns:
            list[MeetingSummaryModel]: List of summary models.
        """
        stmt = (
            select(MeetingSummaryModel)
            .where(MeetingSummaryModel.meeting_id == meeting_id)
            .order_by(MeetingSummaryModel.created_at.desc())
        )
        return list(session.scalars(stmt).all())

    @staticmethod
    def get_latest(
        session: Session,
        meeting_id: str,
        summary_type: str | None = None,
    ) -> MeetingSummaryModel | None:
        """Retrieve the most recent summary for a meeting.

        Args:
            session: Active database session.
            meeting_id: Target meeting UUID string.
            summary_type: Optional filter by summary_type.

        Returns:
            MeetingSummaryModel | None: Latest summary entity or None.
        """
        stmt = select(MeetingSummaryModel).where(
            MeetingSummaryModel.meeting_id == meeting_id
        )
        if summary_type:
            stmt = stmt.where(MeetingSummaryModel.summary_type == summary_type)
        stmt = stmt.order_by(MeetingSummaryModel.created_at.desc()).limit(1)
        return session.scalar(stmt)

    @staticmethod
    def delete_non_final(session: Session, meeting_id: str) -> int:
        """Delete non-final (live/incremental) summaries for reconciliation.

        Args:
            session: Active database session.
            meeting_id: Target meeting UUID string.

        Returns:
            int: Count of deleted non-final records.
        """
        stmt = select(MeetingSummaryModel).where(
            MeetingSummaryModel.meeting_id == meeting_id,
            MeetingSummaryModel.is_final == 0,
        )
        records = list(session.scalars(stmt).all())
        for rec in records:
            session.delete(rec)
        session.flush()
        return len(records)

    @staticmethod
    def update(
        session: Session,
        summary_id: str,
        executive_summary: str,
        bullet_points: list[str],
        key_takeaways: list[str],
        is_final: bool = False,
    ) -> MeetingSummaryModel | None:
        """Update an existing summary record.

        Args:
            session: Active database session.
            summary_id: Target summary UUID string.
            executive_summary: Updated executive narrative text.
            bullet_points: Updated list of bullet points.
            key_takeaways: Updated list of key takeaways.
            is_final: Whether this update marks the summary as final.

        Returns:
            MeetingSummaryModel | None: Updated model or None if not found.
        """
        stmt = select(MeetingSummaryModel).where(MeetingSummaryModel.id == summary_id)
        record = session.scalar(stmt)
        if record:
            record.executive_summary = executive_summary
            record.bullet_points = json.dumps(bullet_points)
            record.key_takeaways = json.dumps(key_takeaways)
            record.is_final = 1 if is_final else 0
            record.updated_at = datetime.now(UTC)
            session.flush()
        return record
