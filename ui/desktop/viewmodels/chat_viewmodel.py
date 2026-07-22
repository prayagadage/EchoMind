"""AI Chat ViewModel managing RAG conversation sessions and citations."""

import uuid
from typing import Any

from modules.assistant.assistant_service import AssistantService
from PyQt6.QtCore import pyqtSignal
from ui.desktop.viewmodels.base_viewmodel import BaseViewModel


class ChatViewModel(BaseViewModel):
    """ViewModel driving AI Chat Panel RAG interaction."""

    message_added = pyqtSignal(dict)
    session_cleared = pyqtSignal()

    def __init__(self, assistant_service: AssistantService | None = None) -> None:
        """Initialize ChatViewModel.

        Args:
            assistant_service: AssistantService instance.
        """
        super().__init__()
        self._assistant = assistant_service
        self._session_id = f"gui-session-{uuid.uuid4().hex[:8]}"
        self._messages: list[dict[str, Any]] = []

    @property
    def session_id(self) -> str:
        """Access active session ID."""
        return self._session_id

    @property
    def messages(self) -> list[dict[str, Any]]:
        """Access list of chat messages."""
        return self._messages

    def send_question(self, question: str, meeting_id: str | None = None) -> None:
        """Send natural language question to AssistantService.

        Args:
            question: Natural language question string.
            meeting_id: Optional meeting UUID filter scope.
        """
        if not question.strip() or not self._assistant:
            return

        # Append user turn
        user_msg = {"sender": "user", "text": question}
        self._messages.append(user_msg)
        self.message_added.emit(user_msg)

        self.set_loading(True)
        try:
            resp = self._assistant.ask(
                session_id=self._session_id, query=question, meeting_id=meeting_id
            )
            citations = [
                {
                    "ref_id": c.ref_id,
                    "meeting_title": c.meeting_title,
                    "entity_type": c.entity_type,
                    "snippet": c.content_snippet,
                }
                for c in resp.citations
            ]
            bot_msg = {
                "sender": "assistant",
                "text": resp.answer,
                "citations": citations,
            }
            self._messages.append(bot_msg)
            self.message_added.emit(bot_msg)
        except Exception as exc:
            self.error_occurred.emit(f"Failed to get AI response: {exc}")
        finally:
            self.set_loading(False)

    def clear_chat(self) -> None:
        """Clear active conversation session."""
        self._messages.clear()
        if self._assistant:
            self._assistant.memory.clear_session(self._session_id)
        self._session_id = f"gui-session-{uuid.uuid4().hex[:8]}"
        self.session_cleared.emit()
