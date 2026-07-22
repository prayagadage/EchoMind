"""Configuration management module using Pydantic Settings.

Parses, validates, and provides strongly-typed configuration settings from
environment variables and optional .env files.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from core.constants import (
    APP_NAME,
    DEFAULT_AUDIO_CHANNELS,
    DEFAULT_AUDIO_CHUNK_SEC,
    DEFAULT_LOG_FILE,
    DEFAULT_SAMPLE_RATE_HZ,
    DEFAULT_TARGET_LANGUAGE,
    VERSION,
)
from core.exceptions import ConfigurationError


class Settings(BaseSettings):
    """Application settings schema backed by environment variables."""

    # Application Metadata
    app_name: str = Field(default=APP_NAME, description="Name of the application")
    app_version: str = Field(default=VERSION, description="Application version")
    app_env: str = Field(
        default="development",
        description="Runtime environment (development, production)",
    )
    debug: bool = Field(default=False, description="Enable debug diagnostics")

    # Logging Settings
    log_level: str = Field(
        default="INFO", description="Log verbosity level (DEBUG, INFO, WARNING, ERROR)"
    )
    log_file_path: Path = Field(
        default=Path(DEFAULT_LOG_FILE), description="Path to log file output"
    )
    log_rotation: str = Field(
        default="10 MB", description="Log file rotation trigger size"
    )
    log_retention: str = Field(default="14 days", description="Log retention duration")
    log_json_format: bool = Field(
        default=False, description="Log in structured JSON format"
    )

    # Audio Settings (Phase 1 preparation)
    audio_sample_rate: int = Field(
        default=DEFAULT_SAMPLE_RATE_HZ, description="Audio sampling rate in Hz"
    )
    audio_channels: int = Field(
        default=DEFAULT_AUDIO_CHANNELS, description="Audio channel count (1=Mono)"
    )
    audio_chunk_sec: int = Field(
        default=DEFAULT_AUDIO_CHUNK_SEC,
        description="Duration of audio chunk in seconds",
    )

    # Multilingual & Translation Settings
    default_source_languages: list[str] = Field(
        default_factory=lambda: ["mr", "hi", "en"],
        description="Supported input languages (Marathi, Hindi, English)",
    )
    target_language: str = Field(
        default=DEFAULT_TARGET_LANGUAGE, description="Target output language"
    )

    # Keyword Alerts
    alert_keywords: list[str] = Field(
        default_factory=lambda: ["Prayag", "EchoMind", "Action Item"],
        description="Keywords to trigger alerts upon detection",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Ensure log level is a valid standard level string."""
        allowed = {"TRACE", "DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL"}
        upper_v = v.upper()
        if upper_v not in allowed:
            raise ValueError(f"Invalid log level '{v}'. Allowed levels: {allowed}")
        return upper_v


# ponytail: Cached settings instance prevents repetitive disk I/O
# and environment parsing.
@lru_cache
def get_settings() -> Settings:
    """Retrieve or initialize the cached application Settings instance.

    Returns:
        Settings: Validated configuration instance.

    Raises:
        ConfigurationError: If environment variable validation fails.
    """
    try:
        return Settings()
    except Exception as exc:
        raise ConfigurationError(
            message=f"Failed to load application configuration: {exc}",
            details={"error": str(exc)},
        ) from exc
