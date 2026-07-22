"""Transcript Viewer View displaying live and historical meeting transcripts."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from ui.desktop.viewmodels.transcript_viewmodel import TranscriptViewModel


class TranscriptView(QWidget):
    """View rendering active meeting transcript items."""

    def __init__(self, viewModel: TranscriptViewModel) -> None:
        """Initialize TranscriptView.

        Args:
            viewModel: TranscriptViewModel instance.
        """
        super().__init__()
        self._vm = viewModel
        self._init_ui()
        self._vm.transcripts_updated.connect(self._on_transcripts_updated)
        self._vm.new_transcript_added.connect(self._on_new_transcript_added)

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Header
        header_layout = QHBoxLayout()
        self._title = QLabel("Transcript Viewer")
        self._title.setStyleSheet("font-size: 24px; font-weight: bold;")
        header_layout.addWidget(self._title)

        reload_btn = QPushButton("Reload")
        reload_btn.setObjectName("secondary")
        reload_btn.clicked.connect(self._vm.load_transcripts)
        header_layout.addWidget(reload_btn, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addLayout(header_layout)

        # Transcript List
        self._list_widget = QListWidget()
        layout.addWidget(self._list_widget)

    def _on_transcripts_updated(self, transcripts: list) -> None:
        self._list_widget.clear()
        for t in transcripts:
            self._add_transcript_item(t)

    def _on_new_transcript_added(self, t: dict) -> None:
        self._add_transcript_item(t)
        self._list_widget.scrollToBottom()

    def _add_transcript_item(self, t: dict) -> None:
        spk = t.get("speaker_name", "Speaker")
        lang = t.get("language", "en").upper()
        ts = t.get("timestamp", 0.0)
        text = t.get("text", "")

        display_text = f"[{ts:.1f}s] [{lang}] {spk}: {text}"
        item = QListWidgetItem(display_text)
        self._list_widget.addItem(item)
