"""Unit test suite for SettingsService and user preference persistence."""

from core.settings_service import SettingsService


def test_settings_service_defaults(tmp_path):
    """SettingsService initializes with default preferences if config file missing."""
    config_file = tmp_path / "test_settings.json"
    service = SettingsService(config_path=config_file)

    settings = service.settings
    assert settings.appearance.theme == "dark"
    assert settings.audio.vad_energy_threshold == 0.002
    assert settings.search.top_k == 5
    assert settings.privacy.auto_delete_audio is True


def test_settings_service_update_and_persistence(tmp_path):
    """SettingsService persists updated settings model to disk."""
    config_file = tmp_path / "test_settings.json"
    service = SettingsService(config_path=config_file)

    current = service.settings
    current.appearance.theme = "light"
    current.audio.input_device = "External Studio Mic"
    current.search.top_k = 10

    service.update_settings(current)
    assert config_file.exists()

    # Re-initialize new service from same file to test disk persistence
    reloaded_service = SettingsService(config_path=config_file)
    reloaded = reloaded_service.settings

    assert reloaded.appearance.theme == "light"
    assert reloaded.audio.input_device == "External Studio Mic"
    assert reloaded.search.top_k == 10
