"""Summary builder gathering structured meeting data for LLM prompt integration."""

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from modules.meeting_intelligence.models import IntelligenceItemModel
from modules.meeting_intelligence.repository import IntelligenceRepository
from modules.storage.models import SpeakerModel, TranscriptModel
from modules.storage.repositories import (
    MeetingRepository,
    SpeakerRepository,
    TranscriptRepository,
)


@dataclass
class SummaryContext:
    """Aggregated data payload containing all meeting context."""

    meeting_id: str
    title: str
    speakers: list[SpeakerModel] = field(default_factory=list)
    transcripts: list[TranscriptModel] = field(default_factory=list)
    intelligence_items: list[IntelligenceItemModel] = field(default_factory=list)

    def format_speakers_text(self) -> str:
        """Format speaker names and colors into text representation.

        Returns:
            str: Formatted speaker roster text.
        """
        if not self.speakers:
            return "No registered speakers."
        lines = []
        for s in self.speakers:
            name = s.display_name or s.temporary_name
            lines.append(f"- {name} (ID: {s.id[:8]}, Temp: {s.temporary_name})")
        return "\n".join(lines)

    def format_intelligence_text(self) -> str:
        """Format pre-extracted intelligence items into ground truth context.

        Returns:
            str: Formatted structured items string.
        """
        if not self.intelligence_items:
            return "No pre-extracted structured items."

        grouped: dict[str, list[IntelligenceItemModel]] = {}
        for item in self.intelligence_items:
            grouped.setdefault(item.item_type, []).append(item)

        lines: list[str] = []
        for item_type, items in grouped.items():
            lines.append(f"### {item_type}S:")
            for it in items:
                details = []
                if it.assignee:
                    details.append(f"Assignee: {it.assignee}")
                if it.due_date:
                    details.append(f"Due: {it.due_date}")
                if it.priority:
                    details.append(f"Priority: {it.priority}")
                meta_str = f" [{', '.join(details)}]" if details else ""
                lines.append(f"- {it.content}{meta_str}")
            lines.append("")

        return "\n".join(lines).strip()

    def format_transcript_text(self) -> str:
        """Format transcripts into chronological text dialogue lines.

        Returns:
            str: Formatted transcript dialogue string.
        """
        if not self.transcripts:
            return "No transcript dialogue available."

        speaker_map = {
            s.id: (s.display_name or s.temporary_name) for s in self.speakers
        }
        lines: list[str] = []

        for t in self.transcripts:
            name = speaker_map.get(t.speaker_id or "", "Unknown")
            ts = f"{t.timestamp:.1f}s"
            text = t.translated_text or t.original_text
            lines.append(f"[{ts}] {name}: {text}")

        return "\n".join(lines)


class SummaryBuilder:
    """Gathers structured meeting information from repositories."""

    @staticmethod
    def build_context(session: Session, meeting_id: str) -> SummaryContext:
        """Gather all meeting context from SQLite database.

        Args:
            session: Active database session.
            meeting_id: Target meeting UUID string.

        Returns:
            SummaryContext: Aggregated meeting data context.
        """
        meeting = MeetingRepository.get_by_id(session, meeting_id)
        title = meeting.title if meeting else "Untitled Meeting"

        speakers = SpeakerRepository.get_by_meeting(session, meeting_id)
        transcripts = TranscriptRepository.get_by_meeting(session, meeting_id)
        intelligence_items = IntelligenceRepository.get_by_meeting(session, meeting_id)

        return SummaryContext(
            meeting_id=meeting_id,
            title=title,
            speakers=speakers,
            transcripts=transcripts,
            intelligence_items=intelligence_items,
        )
