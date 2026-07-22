"""Streaming Speaker Segmentation Subsystem for EchoMind.

Provides SpeakerSegmenter engine, SpeakerService worker, SpeakerRepository persistence,
SpeakerModel entity, and SpeakerEvent bus payloads.
"""

from modules.speaker.models import SpeakerModel
from modules.speaker.speaker_events import (
    SpeakerAssignedEvent,
    SpeakerChangedEvent,
    SpeakerEndedEvent,
    SpeakerStartedEvent,
)
from modules.speaker.speaker_repository import SpeakerRepository
from modules.speaker.speaker_segmenter import (
    SegmenterConfig,
    SegmentResult,
    SpeakerSegmenter,
)
from modules.speaker.speaker_service import SpeakerService

__all__ = [
    "SpeakerModel",
    "SpeakerRepository",
    "SpeakerSegmenter",
    "SegmenterConfig",
    "SegmentResult",
    "SpeakerService",
    "SpeakerStartedEvent",
    "SpeakerEndedEvent",
    "SpeakerChangedEvent",
    "SpeakerAssignedEvent",
]
