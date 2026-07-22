"""Meeting Library ViewModel managing meeting list, search filter, and deletion."""

from typing import Any

from modules.storage.db import DatabaseEngine
from modules.storage.repositories import MeetingRepository
from PyQt6.QtCore import pyqtSignal
from ui.desktop.viewmodels.base_viewmodel import BaseViewModel


class LibraryViewModel(BaseViewModel):
    """ViewModel driving meeting library grid and selection."""

    meetings_updated = pyqtSignal(list)
    meeting_selected = pyqtSignal(str)

    def __init__(self, db_engine: DatabaseEngine) -> None:
        """Initialize LibraryViewModel.

        Args:
            db_engine: DatabaseEngine instance.
        """
        super().__init__()
        self._db = db_engine
        self._meetings: list[dict[str, Any]] = []
        self._filter_query: str = ""

    @property
    def meetings(self) -> list[dict[str, Any]]:
        """Access filtered meeting list."""
        return self._meetings

    def load_meetings(self, filter_query: str = "") -> None:
        """Load and filter meetings from repository.

        Args:
            filter_query: Query filter string.
        """
        self._filter_query = filter_query
        self.set_loading(True)
        try:
            with self._db.session_scope() as session:
                all_m = MeetingRepository.get_recent(session, limit=100)
                m_list = []
                for m in all_m:
                    if filter_query and filter_query.lower() not in m.title.lower():
                        continue
                    m_list.append(
                        {
                            "id": m.id,
                            "title": m.title,
                            "created_at": (
                                m.created_at.strftime("%Y-%m-%d %H:%M")
                                if m.created_at
                                else ""
                            ),
                            "duration": f"{m.duration:.1f}s",
                        }
                    )
                self._meetings = m_list
                self.meetings_updated.emit(self._meetings)
        except Exception as exc:
            self.error_occurred.emit(str(exc))
        finally:
            self.set_loading(False)

    def delete_meeting(self, meeting_id: str) -> None:
        """Delete a meeting from repository.

        Args:
            meeting_id: Target meeting UUID.
        """
        try:
            with self._db.session_scope() as session:
                MeetingRepository.delete(session, meeting_id)
            self.load_meetings(self._filter_query)
        except Exception as exc:
            self.error_occurred.emit(f"Failed to delete meeting: {exc}")
