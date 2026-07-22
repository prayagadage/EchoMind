"""Settings ViewModel managing preference loading and updates."""

from core.settings_service import EchoMindUserSettings, SettingsService
from PyQt6.QtCore import pyqtSignal
from ui.desktop.viewmodels.base_viewmodel import BaseViewModel


class SettingsViewModel(BaseViewModel):
    """ViewModel binding user preference settings UI."""

    settings_updated = pyqtSignal(EchoMindUserSettings)

    def __init__(self, settings_service: SettingsService) -> None:
        """Initialize SettingsViewModel.

        Args:
            settings_service: SettingsService instance.
        """
        super().__init__()
        self._service = settings_service

    @property
    def settings(self) -> EchoMindUserSettings:
        """Access current user settings model."""
        return self._service.settings

    def save_settings(self, new_settings: EchoMindUserSettings) -> None:
        """Save updated settings through SettingsService.

        Args:
            new_settings: Updated EchoMindUserSettings instance.
        """
        try:
            self._service.update_settings(new_settings)
            self.settings_updated.emit(new_settings)
        except Exception as exc:
            self.error_occurred.emit(f"Failed to save settings: {exc}")
