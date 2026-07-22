"""Global Search ViewModel managing vector search queries and results."""

from typing import Any

from modules.search.search_service import SearchService
from PyQt6.QtCore import pyqtSignal
from ui.desktop.viewmodels.base_viewmodel import BaseViewModel


class SearchViewModel(BaseViewModel):
    """ViewModel driving global vector search queries."""

    search_results_updated = pyqtSignal(list)

    def __init__(self, search_service: SearchService | None = None) -> None:
        """Initialize SearchViewModel.

        Args:
            search_service: SearchService instance.
        """
        super().__init__()
        self._search = search_service
        self._results: list[dict[str, Any]] = []

    @property
    def results(self) -> list[dict[str, Any]]:
        """Access list of search results."""
        return self._results

    def execute_search(
        self, query: str, meeting_id: str | None = None, entity_type: str | None = None
    ) -> None:
        """Execute semantic search query.

        Args:
            query: Query string.
            meeting_id: Optional meeting UUID scope filter.
            entity_type: Optional entity type filter.
        """
        if not query.strip() or not self._search:
            self._results = []
            self.search_results_updated.emit([])
            return

        self.set_loading(True)
        try:
            hits = self._search.search(
                query=query, top_k=10, meeting_id=meeting_id, entity_type=entity_type
            )
            res = [
                {
                    "id": h.id,
                    "meeting_id": h.meeting_id,
                    "meeting_title": h.meeting_title,
                    "entity_type": h.entity_type,
                    "content": h.content,
                    "score": f"{h.score:.2f}",
                    "speaker_name": h.speaker_name,
                    "timestamp": h.timestamp,
                }
                for h in hits
            ]
            self._results = res
            self.search_results_updated.emit(self._results)
        except Exception as exc:
            self.error_occurred.emit(f"Search failed: {exc}")
        finally:
            self.set_loading(False)
