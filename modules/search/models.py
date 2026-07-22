"""SQLAlchemy ORM models and SearchResult dataclasses for semantic search."""

import hashlib
import uuid
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field
from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from modules.storage.db import Base


class SearchEntityType(StrEnum):
    """Entity types indexed in the knowledge base."""

    TRANSCRIPT = "TRANSCRIPT"
    SUMMARY = "SUMMARY"
    ACTION_ITEM = "ACTION_ITEM"
    DECISION = "DECISION"
    RISK = "RISK"
    QUESTION = "QUESTION"
    FOLLOW_UP = "FOLLOW_UP"
    DEADLINE = "DEADLINE"


class VectorEmbeddingModel(Base):
    """SQLAlchemy ORM model persisting document vector embeddings."""

    __tablename__ = "vector_embeddings"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    meeting_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False,
    )
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_id: Mapped[str] = mapped_column(String(36), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    vector_json: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        Index("idx_ve_meeting", "meeting_id"),
        Index("idx_ve_entity", "entity_type"),
        Index("idx_ve_source", "source_id"),
        Index("idx_ve_hash", "meeting_id", "entity_type", "content_hash", unique=True),
    )

    def __repr__(self) -> str:
        snippet = self.content[:30]
        return (
            f"<VectorEmbeddingModel(type='{self.entity_type}', "
            f"source='{self.source_id[:8]}', text='{snippet}')>"
        )


def compute_vector_content_hash(entity_type: str, content: str) -> str:
    """Compute deduplication hash for an indexed vector record.

    Args:
        entity_type: SearchEntityType string.
        content: Text content string.

    Returns:
        str: SHA-256 hex digest snippet.
    """
    key = f"{entity_type}:{content.strip().lower()}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


class SearchResult(BaseModel):
    """Data model representing a ranked search result item."""

    id: str = Field(description="Vector record ID")
    meeting_id: str = Field(description="Target meeting UUID")
    meeting_title: str = Field(default="Untitled Meeting")
    entity_type: str = Field(description="Type of entity matched")
    source_id: str = Field(description="Source record UUID")
    content: str = Field(description="Matched content string")
    score: float = Field(description="Cosine similarity score (0.0 to 1.0)")
    speaker_name: str | None = Field(
        default=None, description="Resolved speaker display name"
    )
    timestamp: float | None = Field(
        default=None, description="Audio start timestamp in seconds"
    )
