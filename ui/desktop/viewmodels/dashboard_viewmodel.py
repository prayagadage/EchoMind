"""Dashboard ViewModel providing stats and recent meeting summaries."""

from typing import Any

from modules.storage.db import DatabaseEngine
from modules.storage.repositories import MeetingRepository
from PyQt6.QtCore import pyqtSignal
from ui.desktop.viewmodels.base_viewmodel import BaseViewModel


class DashboardViewModel(BaseViewModel):
    """ViewModel backing recent meetings dashboard view."""

    stats_updated = pyqtSignal(dict)
    recent_meetings_updated = pyqtSignal(list)

    def __init__(self, db_engine: DatabaseEngine) -> None:
        """Initialize DashboardViewModel.

        Args:
            db_engine: DatabaseEngine instance.
        """
        super().__init__()
        self._db = db_engine
        self._stats: dict[str, Any] = {}
        self._recent_meetings: list[dict[str, Any]] = []

    @property
    def stats(self) -> dict[str, Any]:
        """Access calculated dashboard statistics."""
        return self._stats

    @property
    def recent_meetings(self) -> list[dict[str, Any]]:
        """Access recent meetings list."""
        return self._recent_meetings

    def refresh(self) -> None:
        """Reload dashboard stats and recent meetings."""
        self.set_loading(True)
        try:
            with self._db.session_scope() as session:
                meetings = MeetingRepository.get_recent(session, limit=5)
                m_list = []
                for m in meetings:
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
                self._recent_meetings = m_list
                self._stats = {
                    "total_meetings": len(meetings),
                    "active_recordings": 0,
                    "total_action_items": 12,  # Aggregated count placeholder
                }
                self.recent_meetings_updated.emit(self._recent_meetings)
                self.stats_updated.emit(self._stats)
        except Exception as exc:
            self.error_occurred.emit(str(exc))
        finally:
            self.set_loading(False)
