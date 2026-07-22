"""Repository for intelligence item persistence and retrieval."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.meeting_intelligence.models import IntelligenceItemModel


class IntelligenceRepository:
    """Repository managing IntelligenceItem persistence."""

    @staticmethod
    def create(session: Session, item: IntelligenceItemModel) -> IntelligenceItemModel:
        """Persist a new intelligence item.

        Args:
            session: Active SQLAlchemy session.
            item: IntelligenceItemModel instance.

        Returns:
            IntelligenceItemModel: Saved entity.
        """
        session.add(item)
        session.flush()
        return item

    @staticmethod
    def get_by_meeting(
        session: Session, meeting_id: str
    ) -> list[IntelligenceItemModel]:
        """Retrieve all intelligence items for a meeting.

        Args:
            session: Active SQLAlchemy session.
            meeting_id: Target meeting UUID.

        Returns:
            list[IntelligenceItemModel]: Items ordered by creation.
        """
        stmt = (
            select(IntelligenceItemModel)
            .where(IntelligenceItemModel.meeting_id == meeting_id)
            .order_by(IntelligenceItemModel.created_at)
        )
        return list(session.scalars(stmt).all())

    @staticmethod
    def get_by_type(
        session: Session, meeting_id: str, item_type: str
    ) -> list[IntelligenceItemModel]:
        """Retrieve intelligence items filtered by type.

        Args:
            session: Active SQLAlchemy session.
            meeting_id: Target meeting UUID.
            item_type: ItemType string value.

        Returns:
            list[IntelligenceItemModel]: Matching items.
        """
        stmt = (
            select(IntelligenceItemModel)
            .where(
                IntelligenceItemModel.meeting_id == meeting_id,
                IntelligenceItemModel.item_type == item_type,
            )
            .order_by(IntelligenceItemModel.created_at)
        )
        return list(session.scalars(stmt).all())

    @staticmethod
    def exists_by_hash(
        session: Session,
        meeting_id: str,
        item_type: str,
        content_hash: str,
    ) -> bool:
        """Check if an item with this hash already exists.

        Args:
            session: Active SQLAlchemy session.
            meeting_id: Target meeting UUID.
            item_type: ItemType string value.
            content_hash: SHA-256 content hash.

        Returns:
            bool: True if duplicate exists.
        """
        stmt = select(IntelligenceItemModel.id).where(
            IntelligenceItemModel.meeting_id == meeting_id,
            IntelligenceItemModel.item_type == item_type,
            IntelligenceItemModel.content_hash == content_hash,
        )
        return session.scalar(stmt) is not None

    @staticmethod
    def delete_non_final(session: Session, meeting_id: str) -> int:
        """Delete all non-final (incremental) items for reconciliation.

        Args:
            session: Active SQLAlchemy session.
            meeting_id: Target meeting UUID.

        Returns:
            int: Number of deleted items.
        """
        stmt = select(IntelligenceItemModel).where(
            IntelligenceItemModel.meeting_id == meeting_id,
            IntelligenceItemModel.is_final == 0,
        )
        items = list(session.scalars(stmt).all())
        for item in items:
            session.delete(item)
        session.flush()
        return len(items)
