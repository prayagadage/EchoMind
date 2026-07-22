"""Dashboard View displaying meeting stats and recent meeting cards."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from ui.desktop.viewmodels.dashboard_viewmodel import DashboardViewModel


class DashboardView(QWidget):
    """View rendering recent meetings overview and statistics."""

    def __init__(self, viewModel: DashboardViewModel) -> None:
        """Initialize DashboardView.

        Args:
            viewModel: DashboardViewModel instance.
        """
        super().__init__()
        self._vm = viewModel
        self._init_ui()
        self._vm.stats_updated.connect(self._on_stats_updated)
        self._vm.recent_meetings_updated.connect(self._on_recent_meetings_updated)
        self._vm.refresh()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Header Title
        title_label = QLabel("Dashboard")
        title_label.setStyleSheet(
            "font-size: 24px; font-weight: bold; margin-bottom: 12px;"
        )
        layout.addWidget(title_label)

        # Stats Cards Row
        stats_layout = QHBoxLayout()

        self._card_total_meetings = self._create_stat_card("Total Meetings", "0")
        self._card_active_recordings = self._create_stat_card("Active Recordings", "0")
        self._card_action_items = self._create_stat_card("Action Items", "0")

        stats_layout.addWidget(self._card_total_meetings)
        stats_layout.addWidget(self._card_active_recordings)
        stats_layout.addWidget(self._card_action_items)
        layout.addLayout(stats_layout)

        # Recent Meetings List
        recent_title = QLabel("Recent Meetings")
        recent_title.setStyleSheet(
            "font-size: 18px; font-weight: bold; margin-top: 16px;"
        )
        layout.addWidget(recent_title)

        self._recent_list = QListWidget()
        layout.addWidget(self._recent_list)

        refresh_btn = QPushButton("Refresh Dashboard")
        refresh_btn.clicked.connect(self._vm.refresh)
        layout.addWidget(refresh_btn, alignment=Qt.AlignmentFlag.AlignRight)

    def _create_stat_card(self, title: str, initial_value: str) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        c_layout = QVBoxLayout(card)
        t_label = QLabel(title)
        t_label.setStyleSheet("color: #94A3B8; font-size: 12px;")
        v_label = QLabel(initial_value)
        v_label.setObjectName("stat_val")
        v_label.setStyleSheet("font-size: 28px; font-weight: bold; color: #4F46E5;")
        c_layout.addWidget(t_label)
        c_layout.addWidget(v_label)
        return card

    def _on_stats_updated(self, stats: dict) -> None:
        val_lbl = self._card_total_meetings.findChild(QLabel, "stat_val")
        if val_lbl:
            val_lbl.setText(str(stats.get("total_meetings", 0)))

        val_lbl2 = self._card_active_recordings.findChild(QLabel, "stat_val")
        if val_lbl2:
            val_lbl2.setText(str(stats.get("active_recordings", 0)))

        val_lbl3 = self._card_action_items.findChild(QLabel, "stat_val")
        if val_lbl3:
            val_lbl3.setText(str(stats.get("total_action_items", 0)))

    def _on_recent_meetings_updated(self, meetings: list) -> None:
        self._recent_list.clear()
        for m in meetings:
            text = f"📅 {m['title']}  •  {m['created_at']}  •  {m['duration']}"
            self._recent_list.addItem(text)
