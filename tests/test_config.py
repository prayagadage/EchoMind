"""Unit tests for configuration management system."""

import pytest
from core.config import Settings, get_settings
from pydantic import ValidationError


def test_settings_defaults() -> None:
    """Verify default Settings initialization."""
    settings = Settings()
    assert settings.app_name == "EchoMind"
    assert settings.app_version == "0.1.0"
    assert settings.target_language == "en"
    assert "mr" in settings.default_source_languages
    assert "Prayag" in settings.alert_keywords


def test_settings_log_level_validation() -> None:
    """Verify log level validator converts string case and rejects invalid levels."""
    settings = Settings(log_level="info")
    assert settings.log_level == "INFO"

    with pytest.raises(ValidationError):
        Settings(log_level="INVALID_LEVEL")


def test_get_settings_caching() -> None:
    """Verify get_settings returns cached Settings instance."""
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2
