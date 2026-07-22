"""Export Dialog allowing selection of Markdown, JSON, PDF, or DOCX formats."""

from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from ui.desktop.viewmodels.export_viewmodel import ExportViewModel


class ExportDialog(QDialog):
    """Modal dialog for meeting export format selection."""

    def __init__(
        self,
        meeting_id: str,
        viewModel: ExportViewModel,
        parent: QWidget | None = None,
    ) -> None:
        """Initialize ExportDialog.

        Args:
            meeting_id: Target meeting UUID.
            viewModel: ExportViewModel instance.
            parent: Parent Qt widget.
        """
        super().__init__(parent)
        self._meeting_id = meeting_id
        self._vm = viewModel
        self.setWindowTitle("Export Meeting")
        self.setMinimumWidth(400)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)

        title = QLabel("Export Meeting Record")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 12px;")
        layout.addWidget(title)

        form = QFormLayout()
        self._format_combo = QComboBox()
        self._format_combo.addItems(
            ["Markdown (.md)", "JSON (.json)", "PDF (.pdf)", "DOCX (.docx)"]
        )
        form.addRow("Format:", self._format_combo)

        # Path Row
        path_layout = QHBoxLayout()
        self._path_input = QLineEdit()
        self._path_input.setPlaceholderText("/path/to/exported_file")
        path_layout.addWidget(self._path_input)

        browse_btn = QPushButton("Browse...")
        browse_btn.setObjectName("secondary")
        browse_btn.clicked.connect(self._on_browse_clicked)
        path_layout.addWidget(browse_btn)

        form.addRow("Destination:", path_layout)
        layout.addLayout(form)

        # Buttons
        btn_layout = QHBoxLayout()
        export_btn = QPushButton("Export")
        export_btn.clicked.connect(self._on_export_clicked)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("secondary")
        cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(export_btn)
        layout.addLayout(btn_layout)

    def _on_browse_clicked(self) -> None:
        selected_file, _ = QFileDialog.getSaveFileName(
            self, "Save Export File", f"meeting_{self._meeting_id[:8]}"
        )
        if selected_file:
            self._path_input.setText(selected_file)

    def _on_export_clicked(self) -> None:
        path = self._path_input.text()
        if not path:
            return

        combo_str = self._format_combo.currentText().lower()
        if "markdown" in combo_str:
            fmt = "markdown"
        elif "json" in combo_str:
            fmt = "json"
        elif "pdf" in combo_str:
            fmt = "pdf"
        else:
            fmt = "docx"

        self._vm.export(self._meeting_id, fmt, path)
        self.accept()
