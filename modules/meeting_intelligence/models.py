"""SQLAlchemy ORM and Pydantic models for meeting intelligence items.

Defines persistence models for action items, decisions, deadlines,
questions, risks, and follow-ups extracted from meeting transcripts.
"""

import hashlib
import uuid
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field
from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from modules.storage.db import Base


class ItemType(StrEnum):
    """Intelligence item type enumeration."""

    ACTION_ITEM = "ACTION_ITEM"
    DECISION = "DECISION"
    DEADLINE = "DEADLINE"
    QUESTION = "QUESTION"
    RISK = "RISK"
    FOLLOW_UP = "FOLLOW_UP"


class IntelligenceItemModel(Base):
    """SQLAlchemy model for an extracted intelligence item."""

    __tablename__ = "intelligence_items"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    meeting_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False,
    )
    transcript_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("transcripts.id", ondelete="SET NULL"),
        nullable=True,
    )
    speaker_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("speakers.id", ondelete="SET NULL"),
        nullable=True,
    )
    item_type: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    assignee: Mapped[str | None] = mapped_column(String(128), nullable=True)
    due_date: Mapped[str | None] = mapped_column(String(32), nullable=True)
    priority: Mapped[str | None] = mapped_column(String(16), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    source_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_final: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        Index("idx_intel_meeting", "meeting_id"),
        Index("idx_intel_type", "item_type"),
        Index(
            "idx_intel_dedup",
            "meeting_id",
            "item_type",
            "content_hash",
            unique=True,
        ),
    )

    def __repr__(self) -> str:
        snippet = self.content[:30]
        return (
            f"<IntelligenceItemModel("
            f"type='{self.item_type}', "
            f"content='{snippet}')>"
        )


def compute_content_hash(item_type: str, content: str) -> str:
    """Compute deduplication hash for an intelligence item.

    Args:
        item_type: ItemType string value.
        content: Item content text.

    Returns:
        str: SHA-256 hex digest (first 16 chars).
    """
    key = f"{item_type}:{content.strip().lower()}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


# ── Pydantic schemas for LLM JSON output validation ──


class ParsedItem(BaseModel):
    """Single intelligence item parsed from LLM output."""

    type: str = Field(description="Item type")
    content: str = Field(description="Extracted content")
    assignee: str | None = Field(default=None)
    due_date: str | None = Field(default=None)
    priority: str | None = Field(default=None)
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    source_text: str = Field(default="")


class IntelligenceResponse(BaseModel):
    """Schema for the full LLM JSON response."""

    items: list[ParsedItem] = Field(default_factory=list)
