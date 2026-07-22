"""TranslationEvent payload emitted by Translation Engine onto EventBus."""

from dataclasses import dataclass


@dataclass(frozen=True)
class TranslationEvent:
    """Immutable payload emitted when a transcript segment is translated.

    Attributes:
        transcript_id: Unique string identifier of original Transcript.
        meeting_id: Associated meeting UUID string.
        sequence_number: Monotonic transcript segment sequence index.
        source_language: Original language ISO code ('mr', 'hi', 'en').
        target_language: Target translation language ISO code ('en').
        original_text: Raw untranslated transcript text.
        translated_text: Translated English text.
        model_name: Identifier of translation engine/model used.
        timestamp: Unix timestamp when translation occurred.
    """

    transcript_id: str
    meeting_id: str
    sequence_number: int
    source_language: str
    target_language: str
    original_text: str
    translated_text: str
    model_name: str
    timestamp: float
