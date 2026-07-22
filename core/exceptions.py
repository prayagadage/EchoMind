"""Custom exception hierarchy for EchoMind.

Provides structured, domain-specific exceptions to simplify error handling,
prevent silent failures, and ensure actionable stack traces.
"""

from typing import Any


class EchoMindBaseException(Exception):
    """Base exception class for all custom EchoMind runtime errors."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize exception with descriptive message and optional context details.

        Args:
            message: Human-readable error explanation.
            details: Optional dictionary containing debugging metadata.
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message


class ConfigurationError(EchoMindBaseException):
    """Raised when application configuration loading or validation fails."""

    pass


class InitializationError(EchoMindBaseException):
    """Raised when component or container lifespan initialization fails."""

    pass


class AudioDeviceError(EchoMindBaseException):
    """Raised when microphone or system audio capture stream encounters failure."""

    pass


class AudioEngineError(EchoMindBaseException):
    """Raised when AudioEngine lifecycle state machine or stream encounters an error."""

    pass


class AudioBufferOverflowError(EchoMindBaseException):
    """Raised when AudioBuffer exceeds capacity without overwrite permission."""

    pass


class STTInferenceError(EchoMindBaseException):
    """Raised when local speech-to-text inference engine fails."""

    pass


class TranslationError(EchoMindBaseException):
    """Raised when multilingual translation pipeline fails."""

    pass


class KeywordDetectionError(EchoMindBaseException):
    """Raised when keyword matching or pattern scanner fails."""

    pass


class SummarizationError(EchoMindBaseException):
    """Raised when live or final meeting summary generation fails."""

    pass


class IntelligenceError(EchoMindBaseException):
    """Raised when meeting intelligence extraction fails."""

    pass


class SearchError(EchoMindBaseException):
    """Raised when semantic search indexing or vector retrieval fails."""

    pass
