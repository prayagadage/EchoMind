"""ExportService gathering meeting domain models and exporting to formats."""

from enum import Enum
from pathlib import Path
from typing import Any

from loguru import logger

from modules.export.formatters import (
    DOCXFormatter,
    JSONFormatter,
    MarkdownFormatter,
    PDFFormatter,
)
from modules.meeting_intelligence.repository import IntelligenceRepository
from modules.storage.db import DatabaseEngine
from modules.storage.repositories import MeetingRepository, TranscriptRepository
from modules.summary.repository import SummaryRepository


class ExportFormat(Enum):
    """Supported document export formats."""

    MARKDOWN = "markdown"
    JSON = "json"
    PDF = "pdf"
    DOCX = "docx"


class ExportService:
    """Orchestrates gathering meeting data and generating exported files."""

    def __init__(self, db_engine: DatabaseEngine) -> None:
        """Initialize ExportService.

        Args:
            db_engine: DatabaseEngine instance.
        """
        self._db = db_engine
        logger.debug("ExportService initialized.")

    def gather_meeting_data(self, meeting_id: str) -> dict[str, Any]:
        """Fetch complete meeting object tree from repositories.

        Args:
            meeting_id: Target meeting UUID.

        Returns:
            dict[str, Any]: Dictionary payload of meeting details.
        """
        with self._db.session_scope() as session:
            meeting = MeetingRepository.get_by_id(session, meeting_id)
            if not meeting:
                raise ValueError(f"Meeting with ID '{meeting_id}' not found.")

            transcripts = TranscriptRepository.get_by_meeting(session, meeting_id)
            summaries = SummaryRepository.get_by_meeting(session, meeting_id)
            intelligence = IntelligenceRepository.get_by_meeting(session, meeting_id)

            # Build transcript list
            tr_list = []
            for t in transcripts:
                tr_list.append(
                    {
                        "sequence_number": t.sequence_number,
                        "timestamp": t.timestamp,
                        "language": t.language,
                        "text": t.original_text,
                        "translated_text": t.translated_text,
                        "speaker_name": t.speaker.display_name if t.speaker else None,
                    }
                )

            # Build summary dict
            summary_dict = {}
            if summaries:
                latest_summary = summaries[0]
                summary_dict = {
                    "executive_summary": latest_summary.executive_summary,
                    "key_takeaways": latest_summary.key_takeaways,
                    "summary_type": latest_summary.summary_type,
                }

            # Build intelligence lists
            action_items = [
                {
                    "content": i.content,
                    "assignee": i.assignee,
                    "due_date": i.due_date,
                    "priority": i.priority,
                }
                for i in intelligence
                if i.item_type == "ACTION_ITEM"
            ]
            decisions = [
                {"content": i.content, "priority": i.priority}
                for i in intelligence
                if i.item_type == "DECISION"
            ]
            risks = [
                {"content": i.content, "priority": i.priority}
                for i in intelligence
                if i.item_type == "RISK"
            ]

            return {
                "meeting_id": meeting.id,
                "title": meeting.title,
                "created_at": (
                    meeting.created_at.isoformat() if meeting.created_at else ""
                ),
                "duration": meeting.duration,
                "transcripts": tr_list,
                "summary": summary_dict,
                "action_items": action_items,
                "decisions": decisions,
                "risks": risks,
            }

    def export_meeting(
        self,
        meeting_id: str,
        export_format: ExportFormat | str,
        output_path: str | Path,
    ) -> Path:
        """Export a meeting to disk in the target format.

        Args:
            meeting_id: Target meeting UUID.
            export_format: ExportFormat enum or string value.
            output_path: Output file path.

        Returns:
            Path: Absolute Path of written file.
        """
        fmt = (
            ExportFormat(export_format)
            if isinstance(export_format, str)
            else export_format
        )
        target_path = Path(output_path)
        data = self.gather_meeting_data(meeting_id)

        target_path.parent.mkdir(parents=True, exist_ok=True)

        if fmt == ExportFormat.MARKDOWN:
            content = MarkdownFormatter.format(data)
            target_path.write_text(content, encoding="utf-8")
        elif fmt == ExportFormat.JSON:
            content = JSONFormatter.format(data)
            target_path.write_text(content, encoding="utf-8")
        elif fmt == ExportFormat.PDF:
            PDFFormatter.export(data, target_path)
        elif fmt == ExportFormat.DOCX:
            DOCXFormatter.export(data, target_path)
        else:
            raise ValueError(f"Unsupported export format '{fmt}'.")

        logger.info(
            f"Exported Meeting '{meeting_id}' as {fmt.value} to '{target_path}'"
        )
        return target_path.resolve()
