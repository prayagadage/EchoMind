"""Thread-safe session conversation memory for multi-turn dialogue."""

import threading

from modules.assistant.models import ChatTurn


class ConversationMemory:
    """Session-based conversation memory with sliding window turn management."""

    def __init__(self, max_turns: int = 5) -> None:
        """Initialize ConversationMemory.

        Args:
            max_turns: Maximum dialogue turns retained per session.
        """
        self._max_turns = max_turns
        self._sessions: dict[str, list[ChatTurn]] = {}
        self._lock = threading.Lock()

    def add_turn(self, session_id: str, user_query: str, assistant_answer: str) -> None:
        """Record a user query and assistant response turn.

        Args:
            session_id: Session identifier string.
            user_query: User query string.
            assistant_answer: Assistant response string.
        """
        with self._lock:
            turns = self._sessions.setdefault(session_id, [])
            turns.append(
                ChatTurn(user_query=user_query, assistant_answer=assistant_answer)
            )
            if len(turns) > self._max_turns:
                self._sessions[session_id] = turns[-self._max_turns :]

    def get_history(self, session_id: str) -> list[ChatTurn]:
        """Retrieve turn history for a session.

        Args:
            session_id: Session identifier string.

        Returns:
            list[ChatTurn]: List of dialogue turns.
        """
        with self._lock:
            return list(self._sessions.get(session_id, []))

    def format_history_text(self, session_id: str) -> str:
        """Format dialogue history into prompt context string.

        Args:
            session_id: Session identifier string.

        Returns:
            str: Formatted conversation history text.
        """
        history = self.get_history(session_id)
        if not history:
            return ""

        lines = []
        for turn in history:
            lines.append(f"User: {turn.user_query}")
            lines.append(f"Assistant: {turn.assistant_answer}")

        return "\n".join(lines)

    def clear_session(self, session_id: str) -> None:
        """Clear memory for a target session.

        Args:
            session_id: Session identifier string.
        """
        with self._lock:
            self._sessions.pop(session_id, None)
