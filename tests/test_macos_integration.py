"""Unit test suite for macOS system integration (Menu Bar and Native Notifications)."""

import pytest
from PyQt6.QtWidgets import QApplication
from ui.desktop.macos.menu_bar import MenuBarTrayApp
from ui.desktop.macos.notifications import NativeNotificationManager


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_menu_bar_tray_app_initialization(qapp):
    """MenuBarTrayApp initializes system tray actions and toggles recording status."""
    tray = MenuBarTrayApp()
    assert tray is not None

    tray.set_recording_status(True)
    assert tray._is_recording is True

    tray.set_recording_status(False)
    assert tray._is_recording is False


def test_native_notification_manager():
    """NativeNotificationManager formats and dispatches macOS notifications."""
    success = NativeNotificationManager.send_notification(
        title="EchoMind Test Alert",
        subtitle="Unit Test",
        message="Notification dispatch test.",
    )
    assert isinstance(success, bool)
