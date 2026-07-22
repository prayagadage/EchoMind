"""Transcript ViewModel managing transcript view rendering and live streaming."""

from typing import Any

from modules.storage.db import DatabaseEngine
from modules.storage.repositories import TranscriptRepository
from modules.stt.transcript_event import TranscriptEvent
from PyQt6.QtCore import pyqtSignal
from ui.desktop.viewmodels.base_viewmodel import BaseViewModel


class TranscriptViewModel(BaseViewModel):
    """ViewModel binding transcript list and real-time transcript streaming."""

    transcripts_updated = pyqtSignal(list)
    new_transcript_added = pyqtSignal(dict)

    def __init__(self, db_engine: DatabaseEngine) -> None:
        """Initialize TranscriptViewModel.

        Args:
            db_engine: DatabaseEngine instance.
        """
        super().__init__()
        self._db = db_engine
        self._active_meeting_id: str | None = None
        self._transcripts: list[dict[str, Any]] = []

    @property
    def active_meeting_id(self) -> str | None:
        """Access currently active meeting UUID."""
        return self._active_meeting_id

    @property
    def transcripts(self) -> list[dict[str, Any]]:
        """Access active transcript list."""
        return self._transcripts

    def set_meeting(self, meeting_id: str) -> None:
        """Set active meeting scope and load transcripts.

        Args:
            meeting_id: Meeting UUID string.
        """
        self._active_meeting_id = meeting_id
        self.load_transcripts()

    def load_transcripts(self) -> None:
        """Load transcripts for active meeting from database."""
        if not self._active_meeting_id:
            self._transcripts = []
            self.transcripts_updated.emit([])
            return

        self.set_loading(True)
        try:
            with self._db.session_scope() as session:
                records = TranscriptRepository.get_by_meeting(
                    session, self._active_meeting_id
                )
                t_list = []
                for r in records:
                    t_list.append(
                        {
                            "id": r.id,
                            "sequence_number": r.sequence_number,
                            "timestamp": r.timestamp,
                            "language": r.language,
                            "text": r.original_text,
                            "translated_text": r.translated_text,
                            "speaker_name": (
                                r.speaker.display_name if r.speaker else "Speaker"
                            ),
                        }
                    )
                self._transcripts = t_list
                self.transcripts_updated.emit(self._transcripts)
        except Exception as exc:
            self.error_occurred.emit(str(exc))
        finally:
            self.set_loading(False)

    def handle_live_transcript_event(self, event: TranscriptEvent) -> None:
        """Subscriber callback receiving real-time live transcript events.

        Args:
            event: Live TranscriptEvent payload.
        """
        item = {
            "sequence_number": event.sequence_number,
            "timestamp": event.start_time,
            "language": event.language,
            "text": event.text,
            "speaker_name": "Speaker",
        }
        self._transcripts.append(item)
        self.new_transcript_added.emit(item)
