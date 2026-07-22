"""Speech-to-Text (STT) inference module for Apple Silicon.

Provides real-time speech recognition, silence filtering (VAD),
multilingual detection (Marathi, Hindi, English), and transcript event streaming.
"""

from modules.stt.transcript_event import (
    LANG_ENGLISH,
    LANG_HINDI,
    LANG_MARATHI,
    LANG_UNKNOWN,
    TranscriptEvent,
)
from modules.stt.transcript_formatter import TranscriptFormatter
from modules.stt.transcription_pipeline import TranscriptionPipeline
from modules.stt.vad import VoiceActivityDetector
from modules.stt.whisper_engine import MLXWhisperEngine

__all__ = [
    "TranscriptEvent",
    "VoiceActivityDetector",
    "MLXWhisperEngine",
    "TranscriptionPipeline",
    "TranscriptFormatter",
    "LANG_MARATHI",
    "LANG_HINDI",
    "LANG_ENGLISH",
    "LANG_UNKNOWN",
]
