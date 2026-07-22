"""Summary ViewModel managing summary view display and summary generation."""

import json
from typing import Any

from modules.meeting_intelligence.repository import IntelligenceRepository
from modules.storage.db import DatabaseEngine
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

    def set_meeting(self, meeting_id: str) -> None:
        """Set active meeting and load summary data.

        Args:
            meeting_id: Target meeting UUID.
        """
        self._active_meeting_id = meeting_id
        self.load_summary()

    def load_summary(self) -> None:
        """Load summary and intelligence items for active meeting."""
        if not self._active_meeting_id:
            self._summary_data = {}
            self.summary_updated.emit({})
            return

        self.set_loading(True)
        try:
            with self._db.session_scope() as session:
                summaries = SummaryRepository.get_by_meeting(
                    session, self._active_meeting_id
                )
                intelligence = IntelligenceRepository.get_by_meeting(
                    session, self._active_meeting_id
                )

                exec_summary = "No summary generated yet."
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
            self.error_occurred.emit(str(exc))
        finally:
            self.set_loading(False)

    def generate_summary(self) -> None:
        """Trigger async summary generation via SummaryService."""
        if not self._active_meeting_id or not self._summary_service:
            return

        self.set_loading(True)
        try:
            self._summary_service.generate_final_summary(self._active_meeting_id)
            self.load_summary()
        except Exception as exc:
            self.error_occurred.emit(f"Summary generation failed: {exc}")
        finally:
            self.set_loading(False)
