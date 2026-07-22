"""System-wide constants and platform metadata for EchoMind."""

from typing import Final

# Application Metadata
APP_NAME: Final[str] = "EchoMind"
VERSION: Final[str] = "0.1.0"
AUTHOR: Final[str] = "Prayag Adage"

# System Constraints & Target Hardware Specs
TARGET_OS: Final[str] = "Darwin"  # macOS
TARGET_ARCH: Final[str] = "arm64"  # Apple Silicon (M-series)

# Supported Multilingual Options
SUPPORTED_SOURCE_LANGUAGES: Final[set[str]] = {
    "mr",
    "hi",
    "en",
}  # Marathi, Hindi, English
DEFAULT_TARGET_LANGUAGE: Final[str] = "en"  # English translation

# Default Audio Sampling Specs (Apple CoreAudio / Standard Whisper input)
DEFAULT_SAMPLE_RATE_HZ: Final[int] = 16000
DEFAULT_AUDIO_CHANNELS: Final[int] = 1  # Mono audio stream
DEFAULT_AUDIO_CHUNK_SEC: Final[int] = 5

# Default Alert Keywords
DEFAULT_TRIGGER_KEYWORDS: Final[set[str]] = {"Prayag", "EchoMind", "Action Item"}

# File Path Constants
DEFAULT_LOG_DIR: Final[str] = "data/logs"
DEFAULT_LOG_FILE: Final[str] = "data/logs/echomind.log"
