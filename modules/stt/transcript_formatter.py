"""TranscriptFormatter utility for CLI and UI presentation."""

from datetime import datetime
from typing import Any

from modules.stt.transcript_event import TranscriptEvent


class TranscriptFormatter:
    """Formatting utility converting TranscriptEvents into display strings."""

    @staticmethod
    def format_console(event: TranscriptEvent) -> str:
        """Format TranscriptEvent into styled console display line.

        Args:
            event: TranscriptEvent payload.

        Returns:
            str: Colorized timestamped transcript output string.
        """
        timestamp_str = datetime.fromtimestamp(event.start_time).strftime("%H:%M:%S")
        lang_tag = f"[{event.language_label}]"

        return f"[{timestamp_str}] {lang_tag:<10} | {event.text}"

    @staticmethod
    def format_json(event: TranscriptEvent) -> dict[str, Any]:
        """Format TranscriptEvent into serializable dictionary.

        Args:
            event: TranscriptEvent payload.

        Returns:
            Dict[str, Any]: Structured dictionary representation.
        """
        return {
            "sequence_number": event.sequence_number,
            "text": event.text,
            "language": event.language,
            "language_label": event.language_label,
            "start_time": event.start_time,
            "end_time": event.end_time,
            "duration_sec": event.duration_sec,
            "confidence": event.confidence,
            "is_final": event.is_final,
        }
