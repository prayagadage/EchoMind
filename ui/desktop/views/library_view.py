"""Meeting Library View displaying searchable list of meetings."""

from PyQt6.QtCore import Qt, pyqtSignal
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
from ui.desktop.viewmodels.library_viewmodel import LibraryViewModel


class LibraryView(QWidget):
    """View rendering searchable meeting library grid."""

    meeting_selected = pyqtSignal(str)

    def __init__(self, viewModel: LibraryViewModel) -> None:
        """Initialize LibraryView.

        Args:
            viewModel: LibraryViewModel instance.
        """
        super().__init__()
        self._vm = viewModel
        self._init_ui()
        self._vm.meetings_updated.connect(self._on_meetings_updated)
        self._vm.load_meetings()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)

        title = QLabel("Meeting Library")
        title.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 12px;")
        layout.addWidget(title)

        # Search Bar Row
        search_layout = QHBoxLayout()
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Search meetings by title...")
        self._search_input.textChanged.connect(self._on_search_changed)
        search_layout.addWidget(self._search_input)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setObjectName("secondary")
        refresh_btn.clicked.connect(
            lambda: self._vm.load_meetings(self._search_input.text())
        )
        search_layout.addWidget(refresh_btn)
        layout.addLayout(search_layout)

        # Meeting List Widget
        self._meeting_list = QListWidget()
        self._meeting_list.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self._meeting_list)

    def _on_search_changed(self, text: str) -> None:
        self._vm.load_meetings(text)

    def _on_meetings_updated(self, meetings: list) -> None:
        self._meeting_list.clear()
        for m in meetings:
            item_text = (
                f"📁 {m['title']} | Date: {m['created_at']} | Duration: {m['duration']}"
            )
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, m["id"])
            self._meeting_list.addItem(item)

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        m_id = item.data(Qt.ItemDataRole.UserRole)
        if m_id:
            self.meeting_selected.emit(m_id)
