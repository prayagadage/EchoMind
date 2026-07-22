"""SQLAlchemy ORM and Pydantic models for meeting summaries."""

import json
import uuid
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from modules.storage.db import Base


class SummaryType(StrEnum):
    """Meeting summary classification type."""

    EXECUTIVE = "EXECUTIVE"
    BULLET = "BULLET"
    KEY_TAKEAWAYS = "KEY_TAKEAWAYS"
    COMBINED = "COMBINED"


class MeetingSummaryModel(Base):
    """SQLAlchemy ORM model representing a generated meeting summary."""

    __tablename__ = "meeting_summaries"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    meeting_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False,
    )
    summary_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default=SummaryType.COMBINED.value
    )
    executive_summary: Mapped[str] = mapped_column(Text, nullable=False)
    bullet_points: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    key_takeaways: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    model_name: Mapped[str] = mapped_column(
        String(64), nullable=False, default="mlx-community/Qwen3-4B-4bit"
    )
    model_version: Mapped[str] = mapped_column(
        String(16), nullable=False, default="1.0"
    )
    is_final: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        Index("idx_summary_meeting", "meeting_id"),
        Index("idx_summary_type", "summary_type"),
    )

    def get_bullet_points_list(self) -> list[str]:
        """Deserialize stored JSON bullet points.

        Returns:
            list[str]: Deserialized list of bullet point strings.
        """
        try:
            return list(json.loads(self.bullet_points))
        except (json.JSONDecodeError, TypeError):
            return []

    def get_key_takeaways_list(self) -> list[str]:
        """Deserialize stored JSON key takeaways.

        Returns:
            list[str]: Deserialized list of key takeaway strings.
        """
        try:
            return list(json.loads(self.key_takeaways))
        except (json.JSONDecodeError, TypeError):
            return []

    def __repr__(self) -> str:
        snippet = self.executive_summary[:30]
        return (
            f"<MeetingSummaryModel(id='{self.id}', "
            f"type='{self.summary_type}', exec='{snippet}')>"
        )


# ── Pydantic Schema for LLM Response Validation ──


class SummaryResponseSchema(BaseModel):
    """Schema for validating LLM generated JSON summary output."""

    executive_summary: str = Field(
        default="", description="High-level narrative executive summary"
    )
    bullet_points: list[str] = Field(
        default_factory=list, description="Key discussion bullet points"
    )
    key_takeaways: list[str] = Field(
        default_factory=list, description="Critical strategic takeaways"
    )
