"""SpeakerRegistry managing speaker entity creation and color assignment."""

from collections.abc import Sequence

from loguru import logger
from sqlalchemy.orm import Session

from modules.storage.models import SpeakerModel
from modules.storage.repositories import SpeakerRepository

DEFAULT_SPEAKER_COLORS: tuple[str, ...] = (
    "#4F46E5",  # Indigo
    "#10B981",  # Emerald
    "#F59E0B",  # Amber
    "#EF4444",  # Red
    "#8B5CF6",  # Purple
    "#EC4899",  # Pink
    "#06B6D4",  # Cyan
    "#F97316",  # Orange
)


class SpeakerRegistry:
    """Registry managing Speaker persistence, palette allocation, and lookup."""

    def __init__(self, color_palette: Sequence[str] = DEFAULT_SPEAKER_COLORS) -> None:
        """Initialize SpeakerRegistry.

        Args:
            color_palette: Sequence of hex color codes for default speaker assignment.
        """
        self._color_palette = list(color_palette) or list(DEFAULT_SPEAKER_COLORS)

    def register_speaker(
        self,
        session: Session,
        meeting_id: str,
        temporary_name: str,
        display_name: str | None = None,
        color: str | None = None,
    ) -> SpeakerModel:
        """Register and persist a new speaker for a meeting session.

        Args:
            session: Active database session.
            meeting_id: Meeting UUID string.
            temporary_name: Anonymous temporary speaker name (e.g. "Speaker A").
            display_name: Optional human-readable display name (e.g. "Rahul").
            color: Optional hex color code. If omitted, assigned from palette.

        Returns:
            SpeakerModel: Persisted speaker entity.
        """
        if not color:
            existing = SpeakerRepository.get_by_meeting(session, meeting_id)
            color = self._color_palette[len(existing) % len(self._color_palette)]

        speaker = SpeakerModel(
            meeting_id=meeting_id,
            temporary_name=temporary_name,
            display_name=display_name,
            color=color,
        )
        saved = SpeakerRepository.create(session, speaker)
        sid_sub = saved.id[:8]
        mid_sub = meeting_id[:8]
        logger.info(
            f"Registered Speaker '{temporary_name}' ({sid_sub}) in Meeting {mid_sub}"
        )
        return saved

    def get_speaker(self, session: Session, speaker_id: str) -> SpeakerModel | None:
        """Retrieve speaker entity by ID.

        Args:
            session: Active database session.
            speaker_id: Target speaker UUID string.

        Returns:
            SpeakerModel | None: Speaker entity or None.
        """
        return SpeakerRepository.get_by_id(session, speaker_id)

    def list_speakers(self, session: Session, meeting_id: str) -> list[SpeakerModel]:
        """List all speakers associated with a meeting session.

        Args:
            session: Active database session.
            meeting_id: Target meeting UUID string.

        Returns:
            list[SpeakerModel]: List of speakers in the meeting.
        """
        return SpeakerRepository.get_by_meeting(session, meeting_id)

    def get_speaker_by_temp_name(
        self, session: Session, meeting_id: str, temporary_name: str
    ) -> SpeakerModel | None:
        """Find speaker in meeting by temporary name (e.g. 'Speaker A').

        Args:
            session: Active database session.
            meeting_id: Target meeting UUID string.
            temporary_name: Temporary name string.

        Returns:
            SpeakerModel | None: Matching speaker or None.
        """
        speakers = SpeakerRepository.get_by_meeting(session, meeting_id)
        for s in speakers:
            if s.temporary_name == temporary_name:
                return s
        return None
