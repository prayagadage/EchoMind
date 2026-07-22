"""Summary ViewModel managing summary view display and summary generation."""

import json
from typing import Any

from loguru import logger
from modules.meeting_intelligence.repository import IntelligenceRepository
from modules.storage.db import DatabaseEngine
from modules.storage.repositories import MeetingRepository, TranscriptRepository
from modules.summary.repository import SummaryRepository
from modules.summary.summary_service import SummaryService
from PyQt6.QtCore import pyqtSignal
from ui.desktop.viewmodels.base_viewmodel import BaseViewModel


class SummaryViewModel(BaseViewModel):
    """ViewModel orchestrating summary display and regeneration."""

    summary_updated = pyqtSignal(dict)

    def __init__(
        self, db_engine: DatabaseEngine, summary_service: SummaryService | None = None
    ) -> None:
        """Initialize SummaryViewModel.

        Args:
            db_engine: DatabaseEngine instance.
            summary_service: Optional SummaryService instance.
        """
        super().__init__()
        self._db = db_engine
        self._summary_service = summary_service
        self._active_meeting_id: str | None = None
        self._summary_data: dict[str, Any] = {}

    @property
    def summary_data(self) -> dict[str, Any]:
        """Access current summary data dictionary."""
        return self._summary_data

    @property
    def active_meeting_id(self) -> str | None:
        """Get currently active meeting UUID."""
        return self._active_meeting_id

    def set_meeting(self, meeting_id: str) -> None:
        """Set active meeting and load summary data.

        Args:
            meeting_id: Target meeting UUID.
        """
        self._active_meeting_id = meeting_id
        self.load_summary()

    def load_summary(self) -> None:
        """Load summary and intelligence items for active meeting."""
        self.set_loading(True)
        try:
            with self._db.session_scope() as session:
                # Auto-select most recent meeting if none selected
                if not self._active_meeting_id:
                    recent = MeetingRepository.get_recent(session, limit=1)
                    if recent:
                        self._active_meeting_id = recent[0].id

                if not self._active_meeting_id:
                    self._summary_data = {
                        "executive_summary": (
                            "No meetings available yet. Click '🎙️ Start Recording' "
                            "or select a meeting from the Meeting Library."
                        ),
                        "key_takeaways": [],
                        "action_items": [],
                        "decisions": [],
                        "risks": [],
                    }
                    self.summary_updated.emit(self._summary_data)
                    return

                summaries = SummaryRepository.get_by_meeting(
                    session, self._active_meeting_id
                )
                intelligence = IntelligenceRepository.get_by_meeting(
                    session, self._active_meeting_id
                )

                exec_summary = (
                    "No summary generated yet. Click 'Generate Summary' above."
                )
                takeaways: list[str] = []
                if summaries:
                    exec_summary = summaries[0].executive_summary
                    raw_kt = summaries[0].key_takeaways
                    if isinstance(raw_kt, str):
                        try:
                            parsed_kt = json.loads(raw_kt)
                            if isinstance(parsed_kt, list):
                                takeaways = [str(x) for x in parsed_kt]
                        except Exception:
                            takeaways = [raw_kt]
                    elif isinstance(raw_kt, list):
                        takeaways = [str(x) for x in raw_kt]

                action_items = [
                    {
                        "content": i.content,
                        "assignee": i.assignee,
                        "due_date": i.due_date,
                    }
                    for i in intelligence
                    if i.item_type == "ACTION_ITEM"
                ]
                decisions = [
                    i.content for i in intelligence if i.item_type == "DECISION"
                ]
                risks = [i.content for i in intelligence if i.item_type == "RISK"]

                self._summary_data = {
                    "executive_summary": exec_summary,
                    "key_takeaways": takeaways,
                    "action_items": action_items,
                    "decisions": decisions,
                    "risks": risks,
                }
                self.summary_updated.emit(self._summary_data)
        except Exception as exc:
            logger.error(f"Error loading summary: {exc}")
            self.error_occurred.emit(str(exc))
        finally:
            self.set_loading(False)

    def generate_summary(self) -> None:
        """Trigger summary generation via SummaryService."""
        self.set_loading(True)
        try:
            with self._db.session_scope() as session:
                if not self._active_meeting_id:
                    recent = MeetingRepository.get_recent(session, limit=1)
                    if recent:
                        self._active_meeting_id = recent[0].id

            if not self._active_meeting_id:
                self.error_occurred.emit("Please select or record a meeting first.")
                return

            if not self._summary_service:
                self.error_occurred.emit("SummaryService is not configured.")
                return

            # Check if transcripts exist for this meeting
            with self._db.session_scope() as session:
                t_lines = TranscriptRepository.get_by_meeting(
                    session, self._active_meeting_id
                )

            if not t_lines:
                self._summary_data = {
                    "executive_summary": (
                        "No transcript text found for this meeting yet. "
                        "Please speak into your microphone or record audio "
                        "to capture meeting speech."
                    ),
                    "key_takeaways": [],
                    "action_items": [],
                    "decisions": [],
                    "risks": [],
                }
                self.summary_updated.emit(self._summary_data)
                return

            # Generate final summary via service
            logger.info(
                f"Generating summary for meeting '{self._active_meeting_id[:8]}'..."
            )
            res = self._summary_service.generate_final_summary(self._active_meeting_id)
            if not res:
                res = self._summary_service.regenerate_summary(self._active_meeting_id)

            # Reload updated summary
            self.load_summary()
        except Exception as exc:
            logger.error(f"Summary generation error: {exc}")
            self.error_occurred.emit(f"Summary generation failed: {exc}")
        finally:
            self.set_loading(False)
