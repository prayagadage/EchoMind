"""SQLAlchemy 2.0 ORM database models for Meeting and Transcript entities."""

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from modules.storage.db import Base


class MeetingStatus(StrEnum):
    """Meeting lifecycle status enumeration."""

    IN_PROGRESS = "IN_PROGRESS"
    ENDED = "ENDED"


class MeetingModel(Base):
    """SQLAlchemy model representing a meeting session."""

    __tablename__ = "meetings"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=MeetingStatus.IN_PROGRESS.value
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationship to transcript records
    transcripts: Mapped[list["TranscriptModel"]] = relationship(
        "TranscriptModel",
        back_populates="meeting",
        cascade="all, delete-orphan",
        order_by="TranscriptModel.sequence_number",
    )

    def __repr__(self) -> str:
        return (
            f"<MeetingModel(id='{self.id}', title='{self.title}', "
            f"status='{self.status}')>"
        )


class SpeakerModel(Base):
    """SQLAlchemy model representing an active meeting speaker entity."""

    __tablename__ = "speakers"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    meeting_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False
    )
    temporary_name: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        Index("idx_speakers_meeting", "meeting_id"),
        Index("idx_speakers_temp_name", "temporary_name"),
    )

    def __repr__(self) -> str:
        return (
            f"<SpeakerModel(id='{self.id}', meeting_id='{self.meeting_id}', "
            f"name='{self.temporary_name}')>"
        )


class TranscriptModel(Base):
    """SQLAlchemy model representing a transcribed speech segment."""

    __tablename__ = "transcripts"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    meeting_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False
    )
    speaker_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("speakers.id", ondelete="SET NULL"), nullable=True
    )
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    timestamp: Mapped[float] = mapped_column(Float, nullable=False)
    language: Mapped[str] = mapped_column(String(16), nullable=False)
    original_text: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    # Extension columns for future phase compatibility
    translated_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    speaker_label: Mapped[str | None] = mapped_column(String(64), nullable=True)
    embedding_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Relationships
    meeting: Mapped["MeetingModel"] = relationship(
        "MeetingModel", back_populates="transcripts"
    )
    speaker: Mapped[Optional["SpeakerModel"]] = relationship("SpeakerModel")

    __table_args__ = (
        Index("idx_transcripts_meeting_seq", "meeting_id", "sequence_number"),
        Index("idx_transcripts_language", "language"),
        Index("idx_transcripts_speaker", "speaker_id"),
    )

    def __repr__(self) -> str:
        snippet = self.original_text[:20]
        return (
            f"<TranscriptModel(id='{self.id}', seq={self.sequence_number}, "
            f"speaker_id='{self.speaker_id}', text='{snippet}')>"
        )


class TranslationModel(Base):
    """SQLAlchemy model representing a translated transcript segment."""

    __tablename__ = "translations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    transcript_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("transcripts.id", ondelete="CASCADE"), nullable=False
    )
    target_language: Mapped[str] = mapped_column(
        String(16), nullable=False, default="en"
    )
    translated_text: Mapped[str] = mapped_column(Text, nullable=False)
    model_name: Mapped[str] = mapped_column(
        String(64), nullable=False, default="nmt-local"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    # Relationship to transcript
    transcript: Mapped["TranscriptModel"] = relationship("TranscriptModel")

    __table_args__ = (
        Index("idx_translations_transcript", "transcript_id"),
        Index("idx_translations_target_lang", "target_language"),
    )

    def __repr__(self) -> str:
        snippet = self.translated_text[:20]
        return (
            f"<TranslationModel(id='{self.id}', "
            f"transcript_id='{self.transcript_id}', "
            f"target_lang='{self.target_language}', text='{snippet}')>"
        )


class AlertModel(Base):
    """SQLAlchemy model representing a triggered intelligence alert event."""

    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    meeting_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False
    )
    transcript_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("transcripts.id", ondelete="SET NULL"), nullable=True
    )
    rule_name: Mapped[str] = mapped_column(String(64), nullable=False)
    trigger_keyword: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False, default="MEDIUM")
    matched_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        Index("idx_alerts_meeting", "meeting_id"),
        Index("idx_alerts_severity", "severity"),
    )

    def __repr__(self) -> str:
        return (
            f"<AlertModel(id='{self.id}', rule='{self.rule_name}', "
            f"keyword='{self.trigger_keyword}', severity='{self.severity}')>"
        )
