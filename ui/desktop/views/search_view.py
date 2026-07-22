"""Global Search View displaying vector search results and relevance scores."""

from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from ui.desktop.viewmodels.search_viewmodel import SearchViewModel


class SearchView(QWidget):
    """View rendering global vector search results."""

    def __init__(self, viewModel: SearchViewModel) -> None:
        """Initialize SearchView.

        Args:
            viewModel: SearchViewModel instance.
        """
        super().__init__()
        self._vm = viewModel
        self._init_ui()
        self._vm.search_results_updated.connect(self._on_search_results_updated)

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)

        title = QLabel("Global Semantic Search")
        title.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 12px;")
        layout.addWidget(title)

        # Search Bar
        search_layout = QHBoxLayout()
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText(
            "Search across all meetings, transcripts, & action items..."
        )
        self._search_input.returnPressed.connect(self._on_search_clicked)
        search_layout.addWidget(self._search_input)

        search_btn = QPushButton("Search")
        search_btn.clicked.connect(self._on_search_clicked)
        search_layout.addWidget(search_btn)
        layout.addLayout(search_layout)

        # Results List Widget
        self._results_list = QListWidget()
        layout.addWidget(self._results_list)

    def _on_search_clicked(self) -> None:
        query = self._search_input.text()
        self._vm.execute_search(query)

    def _on_search_results_updated(self, results: list) -> None:
        self._results_list.clear()
        if not results:
            self._results_list.addItem("No relevant meeting knowledge items found.")
            return

        for r in results:
            spk = f" ({r['speaker_name']})" if r.get("speaker_name") else ""
            line = (
                f"🔍 [{r['score']}] Meeting: '{r['meeting_title']}' | "
                f"Type: {r['entity_type']}{spk}\n   Snippet: {r['content']}"
            )
            item = QListWidgetItem(line)
            self._results_list.addItem(item)
