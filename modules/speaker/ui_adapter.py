"""SpeakerUIAdapter projecting transcript entities for UI presentation."""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.speaker.speaker_identity_service import SpeakerIdentityService
from modules.storage.models import TranscriptModel
from modules.storage.repositories import SpeakerRepository


@dataclass(frozen=True)
class SpeakerTranscriptProjection:
    """Dataclass projecting transcript record with live speaker metadata."""

    transcript_id: str
    meeting_id: str
    sequence_number: int
    timestamp: float
    speaker_id: str | None
    temporary_speaker_name: str
    effective_speaker_name: str
    speaker_color: str
    original_text: str
    translated_text: str | None
    language: str
    confidence: float


class SpeakerUIAdapter:
    """UI projection adapter decorating transcripts with live speaker names."""

    @staticmethod
    def project_transcript(
        session: Session, transcript: TranscriptModel
    ) -> SpeakerTranscriptProjection:
        """Project a single transcript entity with resolved speaker display name.

        Args:
            session: Active database session.
            transcript: TranscriptModel instance.

        Returns:
            SpeakerTranscriptProjection: Projection payload with live speaker metadata.
        """
        temp_name = "Speaker A"
        eff_name = "Speaker A"
        color = "#4F46E5"

        if transcript.speaker_id:
            spk = SpeakerRepository.get_by_id(session, transcript.speaker_id)
            if spk:
                temp_name = spk.temporary_name
                eff_name = SpeakerIdentityService.get_effective_name(spk)
                color = spk.color

        return SpeakerTranscriptProjection(
            transcript_id=transcript.id,
            meeting_id=transcript.meeting_id,
            sequence_number=transcript.sequence_number,
            timestamp=transcript.timestamp,
            speaker_id=transcript.speaker_id,
            temporary_speaker_name=temp_name,
            effective_speaker_name=eff_name,
            speaker_color=color,
            original_text=transcript.original_text,
            translated_text=transcript.translated_text,
            language=transcript.language,
            confidence=transcript.confidence,
        )

    @staticmethod
    def project_meeting_transcripts(
        session: Session, meeting_id: str
    ) -> list[SpeakerTranscriptProjection]:
        """Project all transcripts in a meeting with live speaker metadata.

        Args:
            session: Active database session.
            meeting_id: Target meeting UUID string.

        Returns:
            list[SpeakerTranscriptProjection]: Chronological projections for UI display.
        """
        speakers = SpeakerRepository.get_by_meeting(session, meeting_id)
        speaker_map = {s.id: s for s in speakers}

        stmt = (
            select(TranscriptModel)
            .where(TranscriptModel.meeting_id == meeting_id)
            .order_by(TranscriptModel.sequence_number)
        )
        transcripts = list(session.scalars(stmt).all())

        projections: list[SpeakerTranscriptProjection] = []
        for t in transcripts:
            spk = speaker_map.get(t.speaker_id) if t.speaker_id else None
            if spk:
                temp_name = spk.temporary_name
                eff_name = SpeakerIdentityService.get_effective_name(spk)
                color = spk.color
            else:
                temp_name = "Unknown Speaker"
                eff_name = "Unknown Speaker"
                color = "#9CA3AF"

            projections.append(
                SpeakerTranscriptProjection(
                    transcript_id=t.id,
                    meeting_id=t.meeting_id,
                    sequence_number=t.sequence_number,
                    timestamp=t.timestamp,
                    speaker_id=t.speaker_id,
                    temporary_speaker_name=temp_name,
                    effective_speaker_name=eff_name,
                    speaker_color=color,
                    original_text=t.original_text,
                    translated_text=t.translated_text,
                    language=t.language,
                    confidence=t.confidence,
                )
            )

        return projections
