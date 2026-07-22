"""Desktop Application runner initializing QApplication and theme stylesheets."""

import sys

from app.container import ApplicationContainer
from PyQt6.QtWidgets import QApplication
from ui.desktop.main_window import MainWindow
from ui.desktop.theme import get_stylesheet


def run_desktop_app(args: list[str] | None = None) -> int:
    """Initialize and run EchoMind desktop Qt application.

    Args:
        args: Command line parameters or None for sys.argv.

    Returns:
        int: Exit status code.
    """
    app = QApplication(args or sys.argv)
    app.setApplicationName("EchoMind")

    container = ApplicationContainer()
    container.initialize()

    # Apply theme stylesheet
    theme_mode = container.settings_service.settings.appearance.theme
    app.setStyleSheet(get_stylesheet(theme_mode))

    window = MainWindow(container)
    window.show()

    exit_code = app.exec()
    container.shutdown()
    return exit_code


if __name__ == "__main__":
    sys.exit(run_desktop_app())
