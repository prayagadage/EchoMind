"""macOS Human Interface Guidelines (HIG) theme styling and QSS stylesheets."""


class ThemeTokens:
    """Color and dimension styling tokens."""

    PRIMARY = "#4F46E5"  # Indigo
    PRIMARY_HOVER = "#4338CA"
    BACKGROUND_DARK = "#0F172A"  # Slate 900
    CARD_DARK = "#1E293B"  # Slate 800
    TEXT_DARK = "#F8FAFC"
    TEXT_MUTED = "#94A3B8"
    BORDER_DARK = "#334155"
    ACCENT_GREEN = "#10B981"
    ACCENT_AMBER = "#F59E0B"
    ACCENT_RED = "#EF4444"

    BACKGROUND_LIGHT = "#F8FAFC"
    CARD_LIGHT = "#FFFFFF"
    TEXT_LIGHT = "#0F172A"
    BORDER_LIGHT = "#E2E8F0"


def get_stylesheet(theme: str = "dark") -> str:
    """Get complete QSS stylesheet for dark or light UI mode.

    Args:
        theme: Theme mode string ('dark' or 'light').

    Returns:
        str: QSS stylesheet string.
    """
    if theme == "light":
        bg = ThemeTokens.BACKGROUND_LIGHT
        card = ThemeTokens.CARD_LIGHT
        text = ThemeTokens.TEXT_LIGHT
        border = ThemeTokens.BORDER_LIGHT
    else:
        bg = ThemeTokens.BACKGROUND_DARK
        card = ThemeTokens.CARD_DARK
        text = ThemeTokens.TEXT_DARK
        border = ThemeTokens.BORDER_DARK

    return f"""
        QMainWindow, QDialog {{
            background-color: {bg};
            color: {text};
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }}
        QWidget {{
            color: {text};
            font-size: 13px;
        }}
        QFrame#card {{
            background-color: {card};
            border: 1px solid {border};
            border-radius: 10px;
            padding: 12px;
        }}
        QPushButton {{
            background-color: {ThemeTokens.PRIMARY};
            color: white;
            border: none;
            border-radius: 6px;
            padding: 8px 16px;
            font-weight: 600;
        }}
        QPushButton:hover {{
            background-color: {ThemeTokens.PRIMARY_HOVER};
        }}
        QPushButton#secondary {{
            background-color: transparent;
            color: {text};
            border: 1px solid {border};
        }}
        QPushButton#secondary:hover {{
            background-color: {border};
        }}
        QLineEdit, QTextEdit, QPlainTextEdit {{
            background-color: {card};
            color: {text};
            border: 1px solid {border};
            border-radius: 6px;
            padding: 8px;
        }}
        QListWidget, QTableWidget {{
            background-color: {card};
            border: 1px solid {border};
            border-radius: 8px;
        }}
        QListWidget::item {{
            padding: 10px;
            border-bottom: 1px solid {border};
        }}
        QListWidget::item:selected {{
            background-color: {ThemeTokens.PRIMARY};
            color: white;
            border-radius: 4px;
        }}
        QTabWidget::pane {{
            border: 1px solid {border};
            background-color: {card};
            border-radius: 8px;
        }}
        QTabBar::tab {{
            background-color: {bg};
            color: {ThemeTokens.TEXT_MUTED};
            padding: 8px 16px;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
        }}
        QTabBar::tab:selected {{
            background-color: {card};
            color: {ThemeTokens.PRIMARY};
            font-weight: bold;
        }}
    """
