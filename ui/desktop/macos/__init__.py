"""macOS System Integration package (Phase 11)."""

from ui.desktop.macos.menu_bar import MenuBarTrayApp
from ui.desktop.macos.notifications import NativeNotificationManager

__all__ = [
    "MenuBarTrayApp",
    "NativeNotificationManager",
]
