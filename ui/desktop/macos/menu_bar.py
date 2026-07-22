"""Native macOS Menu Bar Integration via QSystemTrayIcon."""

from typing import Any

from loguru import logger
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QMenu, QSystemTrayIcon


class MenuBarTrayApp:
    """Manages persistent macOS Menu Bar icon and tray actions."""

    def __init__(self, main_window: Any = None) -> None:
        """Initialize MenuBarTrayApp.

        Args:
            main_window: Reference to main QMainWindow instance.
        """
        self._window = main_window
        self._is_recording = False

        self._tray = QSystemTrayIcon()

        # Build context menu
        self._menu = QMenu()

        self._status_action = QAction("EchoMind: Idle")
        self._status_action.setEnabled(False)
        self._menu.addAction(self._status_action)
        self._menu.addSeparator()

        self._toggle_recording_action = QAction("Start Recording", self._menu)
        self._toggle_recording_action.triggered.connect(self._on_toggle_recording)
        self._menu.addAction(self._toggle_recording_action)

        self._show_window_action = QAction("Open EchoMind Dashboard", self._menu)
        self._show_window_action.triggered.connect(self._on_show_window)
        self._menu.addAction(self._show_window_action)

        self._menu.addSeparator()
        quit_action = QAction("Quit", self._menu)
        quit_action.triggered.connect(self._on_quit)
        self._menu.addAction(quit_action)

        self._tray.setContextMenu(self._menu)
        logger.debug("MenuBarTrayApp initialized.")

    def show(self) -> None:
        """Show system tray icon in macOS menu bar."""
        self._tray.show()

    def set_recording_status(self, is_recording: bool) -> None:
        """Update menu bar status badge and toggle label.

        Args:
            is_recording: True if audio engine is active.
        """
        self._is_recording = is_recording
        if is_recording:
            self._status_action.setText("EchoMind: 🔴 Recording Live")
            self._toggle_recording_action.setText("Stop Recording")
        else:
            self._status_action.setText("EchoMind: Idle")
            self._toggle_recording_action.setText("Start Recording")

    def _on_toggle_recording(self) -> None:
        self.set_recording_status(not self._is_recording)

    def _on_show_window(self) -> None:
        if self._window:
            self._window.show()
            self._window.raise_()
            self._window.activateWindow()

    def _on_quit(self) -> None:
        if self._window:
            self._window.close()
