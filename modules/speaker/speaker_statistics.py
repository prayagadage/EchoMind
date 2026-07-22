"""SpeakerStatisticsCalculator computing metrics and timeline segments."""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.speaker.speaker_identity_service import SpeakerIdentityService
from modules.storage.models import TranscriptModel
from modules.storage.repositories import SpeakerRepository


@dataclass(frozen=True)
class SpeakerStats:
    """Dataclass encapsulating computed speaker statistics."""

    speaker_id: str
    temporary_name: str
    display_name: str | None
    effective_name: str
    color: str
    total_speaking_time_seconds: float
    turn_count: int
    avg_turn_duration_seconds: float
    longest_turn_duration_seconds: float
    first_seen: datetime | None
    last_seen: datetime | None


@dataclass(frozen=True)
class SpeakerTimelineSegment:
    """Dataclass representing a visual timeline block for a speaker's turn."""

    start_time: float
    end_time: float
    duration_seconds: float
    speaker_id: str
    effective_name: str
    color: str
    sequence_number: int
    text_snippet: str


class SpeakerStatisticsCalculator:
    """Calculator computing speaker statistics and timeline models from transcripts."""

    @staticmethod
    def calculate_speaker_stats(
        session: Session, meeting_id: str, speaker_id: str
    ) -> SpeakerStats | None:
        """Calculate statistics for a single speaker in a meeting.

        Args:
            session: Active database session.
            meeting_id: Meeting UUID string.
            speaker_id: Speaker UUID string.

        Returns:
            SpeakerStats | None: Computed statistics or None if not found.
        """
        speaker = SpeakerRepository.get_by_id(session, speaker_id)
        if not speaker or speaker.meeting_id != meeting_id:
            return None

        stmt = (
            select(TranscriptModel)
            .where(
                TranscriptModel.meeting_id == meeting_id,
                TranscriptModel.speaker_id == speaker_id,
            )
            .order_by(TranscriptModel.sequence_number)
        )
        transcripts = list(session.scalars(stmt).all())

        if not transcripts:
            eff_name = SpeakerIdentityService.get_effective_name(speaker)
            return SpeakerStats(
                speaker_id=speaker.id,
                temporary_name=speaker.temporary_name,
                display_name=speaker.display_name,
                effective_name=eff_name,
                color=speaker.color,
                total_speaking_time_seconds=0.0,
                turn_count=0,
                avg_turn_duration_seconds=0.0,
                longest_turn_duration_seconds=0.0,
                first_seen=speaker.created_at,
                last_seen=speaker.last_seen,
            )

        # Estimate segment durations (default 2.5s per turn)
        durations: list[float] = []
        for i, t in enumerate(transcripts):
            if i < len(transcripts) - 1 and transcripts[i + 1].timestamp > t.timestamp:
                delta = transcripts[i + 1].timestamp - t.timestamp
                durations.append(max(0.5, delta))
            else:
                durations.append(2.5)

        total_time = float(sum(durations))
        turns = len(transcripts)
        avg_dur = total_time / turns if turns > 0 else 0.0
        longest_dur = float(max(durations)) if durations else 0.0
        eff_name = SpeakerIdentityService.get_effective_name(speaker)

        return SpeakerStats(
            speaker_id=speaker.id,
            temporary_name=speaker.temporary_name,
            display_name=speaker.display_name,
            effective_name=eff_name,
            color=speaker.color,
            total_speaking_time_seconds=round(total_time, 2),
            turn_count=turns,
            avg_turn_duration_seconds=round(avg_dur, 2),
            longest_turn_duration_seconds=round(longest_dur, 2),
            first_seen=speaker.created_at,
            last_seen=speaker.last_seen,
        )

    @staticmethod
    def calculate_meeting_stats(
        session: Session, meeting_id: str
    ) -> dict[str, SpeakerStats]:
        """Calculate statistics for all speakers in a meeting session.

        Args:
            session: Active database session.
            meeting_id: Target meeting UUID string.

        Returns:
            dict[str, SpeakerStats]: Map of speaker_id -> SpeakerStats.
        """
        speakers = SpeakerRepository.get_by_meeting(session, meeting_id)
        stats_map: dict[str, SpeakerStats] = {}
        for spk in speakers:
            stats = SpeakerStatisticsCalculator.calculate_speaker_stats(
                session, meeting_id, spk.id
            )
            if stats:
                stats_map[spk.id] = stats
        return stats_map

    @staticmethod
    def generate_timeline(
        session: Session, meeting_id: str
    ) -> list[SpeakerTimelineSegment]:
        """Generate timeline visualization segments for a meeting session.

        Args:
            session: Active database session.
            meeting_id: Target meeting UUID string.

        Returns:
            list[SpeakerTimelineSegment]: Chronological list of speaker timeline blocks.
        """
        speakers = SpeakerRepository.get_by_meeting(session, meeting_id)
        speaker_map = {s.id: s for s in speakers}

        stmt = (
            select(TranscriptModel)
            .where(TranscriptModel.meeting_id == meeting_id)
            .order_by(TranscriptModel.sequence_number)
        )
        transcripts = list(session.scalars(stmt).all())

        timeline: list[SpeakerTimelineSegment] = []
        for i, t in enumerate(transcripts):
            spk_id = t.speaker_id or "unknown"
            spk = speaker_map.get(spk_id)
            if spk:
                eff_name = SpeakerIdentityService.get_effective_name(spk)
                color = spk.color
            else:
                eff_name = "Unknown Speaker"
                color = "#9CA3AF"

            start_t = t.timestamp
            if i < len(transcripts) - 1 and transcripts[i + 1].timestamp > start_t:
                end_t = transcripts[i + 1].timestamp
            else:
                end_t = start_t + 2.5

            dur = round(end_t - start_t, 2)
            orig = t.original_text
            snippet = orig[:40] + ("..." if len(orig) > 40 else "")

            timeline.append(
                SpeakerTimelineSegment(
                    start_time=round(start_t, 2),
                    end_time=round(end_t, 2),
                    duration_seconds=dur,
                    speaker_id=spk_id,
                    effective_name=eff_name,
                    color=color,
                    sequence_number=t.sequence_number,
                    text_snippet=snippet,
                )
            )

        return timeline
