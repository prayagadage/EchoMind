"""Repository managing VectorEmbeddingModel SQL database operations."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.search.models import VectorEmbeddingModel


class VectorRepository:
    """Repository managing persistent VectorEmbeddingModel ORM records."""

    @staticmethod
    def create(session: Session, model: VectorEmbeddingModel) -> VectorEmbeddingModel:
        """Persist a new vector embedding record.

        Args:
            session: Active database session.
            model: VectorEmbeddingModel instance.

        Returns:
            VectorEmbeddingModel: Persisted entity.
        """
        session.add(model)
        session.flush()
        return model

    @staticmethod
    def get_by_meeting(session: Session, meeting_id: str) -> list[VectorEmbeddingModel]:
        """Retrieve all vector embedding records for a meeting.

        Args:
            session: Active database session.
            meeting_id: Target meeting UUID string.

        Returns:
            list[VectorEmbeddingModel]: List of vector embedding records.
        """
        stmt = (
            select(VectorEmbeddingModel)
            .where(VectorEmbeddingModel.meeting_id == meeting_id)
            .order_by(VectorEmbeddingModel.created_at)
        )
        return list(session.scalars(stmt).all())

    @staticmethod
    def exists_by_hash(
        session: Session,
        meeting_id: str,
        entity_type: str,
        content_hash: str,
    ) -> bool:
        """Check if a vector with this content hash already exists for the meeting.

        Args:
            session: Active database session.
            meeting_id: Target meeting UUID string.
            entity_type: SearchEntityType string value.
            content_hash: Content hash digest string.

        Returns:
            bool: True if duplicate vector exists.
        """
        stmt = select(VectorEmbeddingModel.id).where(
            VectorEmbeddingModel.meeting_id == meeting_id,
            VectorEmbeddingModel.entity_type == entity_type,
            VectorEmbeddingModel.content_hash == content_hash,
        )
        return session.scalar(stmt) is not None

    @staticmethod
    def delete_by_meeting(session: Session, meeting_id: str) -> int:
        """Delete all vector embedding database records for a target meeting.

        Args:
            session: Active database session.
            meeting_id: Target meeting UUID string.

        Returns:
            int: Number of deleted records.
        """
        stmt = select(VectorEmbeddingModel).where(
            VectorEmbeddingModel.meeting_id == meeting_id
        )
        records = list(session.scalars(stmt).all())
        for rec in records:
            session.delete(rec)
        session.flush()
        return len(records)
