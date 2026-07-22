"""Event dataclass payloads emitted by the Speaker Segmentation Subsystem."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SpeakerStartedEvent:
    """Emitted when a speaker begins a new speech segment."""

    speaker_id: str
    temporary_name: str
    timestamp: float


@dataclass(frozen=True)
class SpeakerEndedEvent:
    """Emitted when a speaker stops speaking."""

    speaker_id: str
    temporary_name: str
    duration: float
    timestamp: float


@dataclass(frozen=True)
class SpeakerChangedEvent:
    """Emitted when active speaker transitions from one speaker to another."""

    previous_speaker_id: str | None
    new_speaker_id: str
    new_temporary_name: str
    timestamp: float


@dataclass(frozen=True)
class SpeakerAssignedEvent:
    """Emitted when a transcript segment is assigned a speaker ID."""

    transcript_id: str
    meeting_id: str
    speaker_id: str
    temporary_name: str
    timestamp: float


@dataclass(frozen=True)
class SpeakerUpdatedEvent:
    """Emitted when a speaker is renamed or assigned a new color code."""

    speaker_id: str
    meeting_id: str
    temporary_name: str
    display_name: str | None
    color: str
    timestamp: float


@dataclass(frozen=True)
class SpeakerMergedEvent:
    """Emitted when one speaker is merged into another speaker."""

    meeting_id: str
    target_speaker_id: str
    destination_speaker_id: str
    affected_transcripts_count: int
    timestamp: float
