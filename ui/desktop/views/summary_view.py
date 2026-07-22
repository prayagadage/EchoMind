"""Summary View displaying executive summary, takeaways, action items, and decisions."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from ui.desktop.viewmodels.summary_viewmodel import SummaryViewModel


class SummaryView(QWidget):
    """View rendering structured meeting summary."""

    def __init__(self, viewModel: SummaryViewModel) -> None:
        """Initialize SummaryView.

        Args:
            viewModel: SummaryViewModel instance.
        """
        super().__init__()
        self._vm = viewModel
        self._init_ui()
        self._vm.summary_updated.connect(self._on_summary_updated)

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Header Row
        header_layout = QHBoxLayout()
        title = QLabel("Meeting Summary")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        header_layout.addWidget(title)

        gen_btn = QPushButton("Generate Summary")
        gen_btn.clicked.connect(self._vm.generate_summary)
        header_layout.addWidget(gen_btn, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addLayout(header_layout)

        # Scroll Area Content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content_widget = QWidget()
        c_layout = QVBoxLayout(content_widget)

        # Executive Summary Box
        c_layout.addWidget(QLabel("<b>Executive Summary</b>"))
        self._exec_summary_text = QTextEdit()
        self._exec_summary_text.setReadOnly(True)
        self._exec_summary_text.setMaximumHeight(100)
        c_layout.addWidget(self._exec_summary_text)

        # Key Takeaways
        c_layout.addWidget(QLabel("<b>Key Takeaways</b>"))
        self._takeaways_list = QListWidget()
        self._takeaways_list.setMaximumHeight(120)
        c_layout.addWidget(self._takeaways_list)

        # Action Items
        c_layout.addWidget(QLabel("<b>Action Items</b>"))
        self._actions_list = QListWidget()
        self._actions_list.setMaximumHeight(140)
        c_layout.addWidget(self._actions_list)

        # Decisions
        c_layout.addWidget(QLabel("<b>Decisions & Key Agreements</b>"))
        self._decisions_list = QListWidget()
        self._decisions_list.setMaximumHeight(120)
        c_layout.addWidget(self._decisions_list)

        scroll.setWidget(content_widget)
        layout.addWidget(scroll)

    def _on_summary_updated(self, summary: dict) -> None:
        self._exec_summary_text.setText(
            summary.get("executive_summary", "No summary available.")
        )

        self._takeaways_list.clear()
        for kt in summary.get("key_takeaways", []):
            self._takeaways_list.addItem(f"• {kt}")

        self._actions_list.clear()
        for ai in summary.get("action_items", []):
            assignee = f" (@{ai['assignee']})" if ai.get("assignee") else ""
            due = f" [Due: {ai['due_date']}]" if ai.get("due_date") else ""
            self._actions_list.addItem(f"☑ {ai['content']}{assignee}{due}")

        self._decisions_list.clear()
        for d in summary.get("decisions", []):
            self._decisions_list.addItem(f"✓ {d}")
