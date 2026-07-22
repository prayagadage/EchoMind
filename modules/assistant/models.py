"""Data models for AI Meeting Assistant and Conversational RAG responses."""

import time
from dataclasses import dataclass, field

from pydantic import BaseModel, Field


@dataclass
class ChatTurn:
    """Dataclass representing a single turn in a multi-turn conversation."""

    user_query: str
    assistant_answer: str
    timestamp: float = field(default_factory=time.time)


class Citation(BaseModel):
    """Source attribution citation model referencing underlying meeting records."""

    ref_id: str = Field(description="Reference tag identifier (e.g. Ref 1)")
    meeting_id: str = Field(description="Target meeting UUID")
    meeting_title: str = Field(default="Untitled Meeting")
    entity_type: str = Field(description="Type of indexed entity")
    source_id: str = Field(description="Source entity UUID")
    content_snippet: str = Field(description="Original context snippet text")
    speaker_name: str | None = Field(
        default=None, description="Resolved speaker display name"
    )
    timestamp: float | None = Field(
        default=None, description="Audio start timestamp in seconds"
    )


class AssistantResponse(BaseModel):
    """Complete RAG response object returned by AssistantService."""

    session_id: str = Field(description="Conversation session identifier")
    query: str = Field(description="User natural language question")
    answer: str = Field(description="Synthesized grounded answer")
    citations: list[Citation] = Field(
        default_factory=list, description="Source citations for answer claims"
    )
    retrieved_count: int = Field(
        default=0, description="Count of retrieved vector context records"
    )
    model_name: str = Field(
        default="mlx-community/Qwen3-4B-4bit", description="LLM provider model ID"
    )
