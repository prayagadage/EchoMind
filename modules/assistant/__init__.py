"""AI Meeting Assistant Module (Phase 10).

Provides natural language question answering over indexed meeting knowledge
using Retrieval-Augmented Generation (RAG), multi-turn memory, and source citations.
"""

from modules.assistant.assistant_service import AssistantService
from modules.assistant.context_builder import ContextBuilder, GroundedContextPayload
from modules.assistant.conversation_memory import ConversationMemory
from modules.assistant.models import AssistantResponse, ChatTurn, Citation
from modules.assistant.prompt_builder import AssistantPromptBuilder
from modules.assistant.query_parser import ParsedQuery, QueryParser
from modules.assistant.response_generator import ResponseGenerator
from modules.assistant.retrieval_service import RetrievalService

__all__ = [
    "AssistantPromptBuilder",
    "AssistantResponse",
    "AssistantService",
    "ChatTurn",
    "Citation",
    "ContextBuilder",
    "ConversationMemory",
    "GroundedContextPayload",
    "ParsedQuery",
    "QueryParser",
    "ResponseGenerator",
    "RetrievalService",
]
