"""MainWindow container shell with sidebar navigation and recording controls."""

from app.container import ApplicationContainer
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from ui.desktop.macos.menu_bar import MenuBarTrayApp
from ui.desktop.views.chat_view import ChatView
from ui.desktop.views.dashboard_view import DashboardView
from ui.desktop.views.export_dialog import ExportDialog
from ui.desktop.views.library_view import LibraryView
from ui.desktop.views.search_view import SearchView
from ui.desktop.views.settings_view import SettingsView
from ui.desktop.views.summary_view import SummaryView
from ui.desktop.views.transcript_view import TranscriptView


class MainWindow(QMainWindow):
    """Primary macOS application container shell window."""

    def __init__(self, container: ApplicationContainer) -> None:
        """Initialize MainWindow shell.

        Args:
            container: ApplicationContainer instance.
        """
        super().__init__()
        self._container = container
        self.setWindowTitle("EchoMind — Offline AI Meeting Assistant")
        self.resize(1100, 720)

        # Initialize ViewModels
        from ui.desktop.viewmodels.chat_viewmodel import ChatViewModel
        from ui.desktop.viewmodels.dashboard_viewmodel import DashboardViewModel
        from ui.desktop.viewmodels.export_viewmodel import ExportViewModel
        from ui.desktop.viewmodels.library_viewmodel import LibraryViewModel
        from ui.desktop.viewmodels.search_viewmodel import SearchViewModel
        from ui.desktop.viewmodels.settings_viewmodel import SettingsViewModel
        from ui.desktop.viewmodels.summary_viewmodel import SummaryViewModel
        from ui.desktop.viewmodels.transcript_viewmodel import TranscriptViewModel

        self._dashboard_vm = DashboardViewModel(container.db_engine)
        self._library_vm = LibraryViewModel(container.db_engine)
        self._transcript_vm = TranscriptViewModel(container.db_engine)
        self._summary_vm = SummaryViewModel(
            container.db_engine, container.summary_service
        )
        self._chat_vm = ChatViewModel(container.assistant_service)
        self._search_vm = SearchViewModel(container.search_service)
        self._settings_vm = SettingsViewModel(container.settings_service)
        self._export_vm = ExportViewModel(container.export_service)

        self._menu_bar_tray = MenuBarTrayApp(self)
        self._menu_bar_tray.show()

        # Recording timer
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._update_recording_timer)

        self._init_ui()

        # Connect live transcript listener to transcript viewmodel
        self._container.recording_service.add_transcript_listener(
            self._transcript_vm.handle_live_transcript_event
        )

    def _init_ui(self) -> None:
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Side Navigation Drawer
        sidebar = QFrame()
        sidebar.setObjectName("card")
        sidebar.setFixedWidth(220)
        s_layout = QVBoxLayout(sidebar)

        brand_lbl = QLabel("🧠 EchoMind")
        brand_lbl.setStyleSheet(
            "font-size: 18px; font-weight: bold; color: #4F46E5; margin-bottom: 8px;"
        )
        s_layout.addWidget(brand_lbl)

        # Start / Stop Recording Control Button
        self._record_btn = QPushButton("🎙️ Start Recording")
        self._record_btn.setStyleSheet(
            "background-color: #4F46E5; color: white; font-weight: bold; "
            "padding: 10px; border-radius: 8px; font-size: 13px;"
        )
        self._record_btn.clicked.connect(self._toggle_recording)
        s_layout.addWidget(self._record_btn)

        self._nav_list = QListWidget()
        self._nav_list.addItem("Dashboard")
        self._nav_list.addItem("Meeting Library")
        self._nav_list.addItem("Transcript Viewer")
        self._nav_list.addItem("Meeting Summary")
        self._nav_list.addItem("AI Assistant Chat")
        self._nav_list.addItem("Global Search")
        self._nav_list.addItem("Settings")
        self._nav_list.currentRowChanged.connect(self._on_nav_changed)
        s_layout.addWidget(self._nav_list)

        # Export Button at bottom of sidebar
        export_btn = QPushButton("Export Meeting...")
        export_btn.setObjectName("secondary")
        export_btn.clicked.connect(self._on_export_clicked)
        s_layout.addWidget(export_btn)

        main_layout.addWidget(sidebar)

        # Main Content Stack
        self._stack = QStackedWidget()

        self._dashboard_view = DashboardView(
            self._dashboard_vm, start_record_callback=self._toggle_recording
        )
        self._library_view = LibraryView(self._library_vm)
        self._transcript_view = TranscriptView(self._transcript_vm)
        self._summary_view = SummaryView(self._summary_vm)
        self._chat_view = ChatView(self._chat_vm)
        self._search_view = SearchView(self._search_vm)
        self._settings_view = SettingsView(self._settings_vm)

        self._stack.addWidget(self._dashboard_view)
        self._stack.addWidget(self._library_view)
        self._stack.addWidget(self._transcript_view)
        self._stack.addWidget(self._summary_view)
        self._stack.addWidget(self._chat_view)
        self._stack.addWidget(self._search_view)
        self._stack.addWidget(self._settings_view)

        main_layout.addWidget(self._stack)

        # Connect library selection to transcript & summary views
        self._library_view.meeting_selected.connect(self._on_meeting_selected)

    def _toggle_recording(self) -> None:
        rec_service = self._container.recording_service
        if not rec_service.is_recording:
            meeting_id = rec_service.start_recording()
            self._transcript_vm.set_meeting(meeting_id)
            self._summary_vm.set_meeting(meeting_id)
            self._menu_bar_tray.set_recording_status(True)
            self._record_btn.setStyleSheet(
                "background-color: #EF4444; color: white; font-weight: bold; "
                "padding: 10px; border-radius: 8px; font-size: 13px;"
            )
            self._timer.start()
            self._update_recording_timer()
            # Switch view to Transcript Viewer
            self._nav_list.setCurrentRow(2)
        else:
            self._timer.stop()
            completed_id = rec_service.stop_recording()
            self._menu_bar_tray.set_recording_status(False)
            self._record_btn.setText("🎙️ Start Recording")
            self._record_btn.setStyleSheet(
                "background-color: #4F46E5; color: white; font-weight: bold; "
                "padding: 10px; border-radius: 8px; font-size: 13px;"
            )
            # Refresh dashboard and library
            self._dashboard_vm.refresh()
            self._library_vm.load_meetings()
            if completed_id:
                self._transcript_vm.set_meeting(completed_id)
                self._summary_vm.set_meeting(completed_id)

    def _update_recording_timer(self) -> None:
        rec_service = self._container.recording_service
        if rec_service.is_recording:
            secs = int(rec_service.elapsed_seconds)
            mins = secs // 60
            secs = secs % 60
            self._record_btn.setText(f"🔴 Recording ({mins:02d}:{secs:02d})")
            self._dashboard_vm.stats["active_recordings"] = 1
            self._dashboard_view._on_stats_updated(self._dashboard_vm.stats)

    def _on_nav_changed(self, index: int) -> None:
        if 0 <= index < self._stack.count():
            self._stack.setCurrentIndex(index)

    def _on_meeting_selected(self, meeting_id: str) -> None:
        self._transcript_vm.set_meeting(meeting_id)
        self._summary_vm.set_meeting(meeting_id)
        self._nav_list.setCurrentRow(2)

    def _on_export_clicked(self) -> None:
        meeting_id = self._transcript_vm.active_meeting_id or "default-meeting-id"
        dlg = ExportDialog(
            meeting_id=meeting_id, viewModel=self._export_vm, parent=self
        )
        dlg.exec()
