"""Thread-safe SettingsService managing application configuration persistence."""

import json
import threading
from pathlib import Path

from loguru import logger
from pydantic import BaseModel, Field


class AudioUISettings(BaseModel):
    """Audio input configuration parameters."""

    input_device: str = Field(
        default="default", description="Selected audio device ID/name"
    )
    chunk_sec: float = Field(default=0.5, description="Audio capture chunk duration")
    vad_energy_threshold: float = Field(
        default=0.002, description="VAD RMS energy threshold"
    )


class AIModelUISettings(BaseModel):
    """AI Model parameters for Whisper and Qwen."""

    whisper_model: str = Field(
        default="mlx-community/whisper-small-mlx", description="Whisper model ID"
    )
    llm_model: str = Field(
        default="mlx-community/Qwen3-4B-4bit", description="LLM provider model ID"
    )
    temperature: float = Field(default=0.3, description="LLM sampling temperature")
    max_tokens: int = Field(default=2048, description="LLM token budget limit")


class SearchUISettings(BaseModel):
    """Search and Knowledge Base configurations."""

    top_k: int = Field(default=5, description="Default vector search top-k hits")
    min_score_threshold: float = Field(
        default=0.01, description="Minimum similarity score"
    )


class AppearanceUISettings(BaseModel):
    """UI Appearance preferences."""

    theme: str = Field(
        default="dark", description="UI theme ('dark', 'light', 'system')"
    )
    font_size: int = Field(default=13, description="Base application font size")
    compact_mode: bool = Field(default=False, description="Enable compact list layouts")


class PrivacyUISettings(BaseModel):
    """Privacy and local storage options."""

    analytics_enabled: bool = Field(
        default=False, description="Local telemetry reporting"
    )
    auto_delete_audio: bool = Field(
        default=True, description="Purge raw audio post-transcript"
    )


class EchoMindUserSettings(BaseModel):
    """Aggregated user setting preferences model."""

    audio: AudioUISettings = Field(default_factory=AudioUISettings)
    ai_model: AIModelUISettings = Field(default_factory=AIModelUISettings)
    search: SearchUISettings = Field(default_factory=SearchUISettings)
    appearance: AppearanceUISettings = Field(default_factory=AppearanceUISettings)
    privacy: PrivacyUISettings = Field(default_factory=PrivacyUISettings)


class SettingsService:
    """Manages reading, updating, and persisting user settings to disk."""

    def __init__(self, config_path: str | Path | None = None) -> None:
        """Initialize SettingsService.

        Args:
            config_path: Path to user settings JSON file.
        """
        if config_path is None:
            config_path = (
                Path.home()
                / ".gemini"
                / "antigravity-ide"
                / "echomind_user_settings.json"
            )
        self._config_path = Path(config_path)
        self._lock = threading.Lock()
        self._settings = self._load()

    @property
    def settings(self) -> EchoMindUserSettings:
        """Get copy of current user settings."""
        with self._lock:
            return self._settings.model_copy(deep=True)

    def update_settings(self, new_settings: EchoMindUserSettings) -> None:
        """Update and persist user settings to disk.

        Args:
            new_settings: Updated EchoMindUserSettings instance.
        """
        with self._lock:
            self._settings = new_settings.model_copy(deep=True)
            self._save_in_lock()
        logger.info("User settings updated and persisted successfully.")

    def _load(self) -> EchoMindUserSettings:
        """Load settings from JSON file if exists, else return default."""
        if not self._config_path.exists():
            return EchoMindUserSettings()

        try:
            content = self._config_path.read_text(encoding="utf-8")
            data = json.loads(content)
            return EchoMindUserSettings.model_validate(data)
        except Exception as exc:
            logger.warning(
                f"Failed to load user settings from '{self._config_path}': {exc}; "
                "using default settings."
            )
            return EchoMindUserSettings()

    def _save_in_lock(self) -> None:
        """Save settings model to JSON file under lock."""
        try:
            self._config_path.parent.mkdir(parents=True, exist_ok=True)
            data = self._settings.model_dump()
            self._config_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as exc:
            logger.error(f"Failed to persist settings to '{self._config_path}': {exc}")
