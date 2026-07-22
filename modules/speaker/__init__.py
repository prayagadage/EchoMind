"""Streaming Speaker Segmentation Subsystem for EchoMind.

Provides SpeakerSegmenter engine, SpeakerService worker, SpeakerRepository persistence,
SpeakerModel entity, and SpeakerEvent bus payloads.
"""

from modules.speaker.models import SpeakerModel
from modules.speaker.speaker_events import (
    SpeakerAssignedEvent,
    SpeakerChangedEvent,
    SpeakerEndedEvent,
    SpeakerMergedEvent,
    SpeakerStartedEvent,
    SpeakerUpdatedEvent,
)
from modules.speaker.speaker_identity_service import SpeakerIdentityService
from modules.speaker.speaker_merge_service import SpeakerMergeService
from modules.speaker.speaker_registry import SpeakerRegistry
from modules.speaker.speaker_repository import SpeakerRepository
from modules.speaker.speaker_segmenter import (
    SegmenterConfig,
    SegmentResult,
    SpeakerSegmenter,
)
from modules.speaker.speaker_service import SpeakerService
from modules.speaker.speaker_statistics import (
    SpeakerStatisticsCalculator,
    SpeakerStats,
    SpeakerTimelineSegment,
)
from modules.speaker.ui_adapter import (
    SpeakerTranscriptProjection,
    SpeakerUIAdapter,
)

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
    "SpeakerUpdatedEvent",
    "SpeakerMergedEvent",
    "SpeakerRegistry",
    "SpeakerIdentityService",
    "SpeakerMergeService",
    "SpeakerStats",
    "SpeakerStatisticsCalculator",
    "SpeakerTimelineSegment",
    "SpeakerTranscriptProjection",
    "SpeakerUIAdapter",
]
