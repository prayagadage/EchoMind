"""AssistantService orchestrating natural language RAG Q&A with memory and citations."""

from core.exceptions import AssistantError
from core.llm.provider import LLMProvider
from loguru import logger

from modules.assistant.context_builder import ContextBuilder
from modules.assistant.conversation_memory import ConversationMemory
from modules.assistant.models import AssistantResponse
from modules.assistant.prompt_builder import AssistantPromptBuilder
from modules.assistant.query_parser import QueryParser
from modules.assistant.response_generator import ResponseGenerator
from modules.assistant.retrieval_service import RetrievalService


class AssistantService:
    """Orchestrates Retrieval-Augmented Generation (RAG) for AI meeting Q&A."""

    def __init__(
        self,
        llm: LLMProvider,
        retrieval_service: RetrievalService,
        memory: ConversationMemory | None = None,
        max_tokens: int = 2048,
    ) -> None:
        """Initialize AssistantService.

        Args:
            llm: LLM provider instance.
            retrieval_service: RetrievalService instance.
            memory: Optional ConversationMemory instance.
            max_tokens: LLM token budget limit.
        """
        self._llm = llm
        self._retrieval = retrieval_service
        self._memory = memory or ConversationMemory()
        self._max_tokens = max_tokens
        logger.debug("AssistantService initialized.")

    @property
    def memory(self) -> ConversationMemory:
        """Access conversation memory instance."""
        return self._memory

    def ask(
        self,
        session_id: str,
        query: str,
        meeting_id: str | None = None,
        top_k: int = 5,
        min_score: float = 0.0,
    ) -> AssistantResponse:
        """Process a natural language user question using RAG.

        Args:
            session_id: Unique session/conversation ID string.
            query: User natural language question.
            meeting_id: Optional meeting UUID scope filter.
            top_k: Maximum number of retrieved search hits.
            min_score: Minimum similarity score threshold.

        Returns:
            AssistantResponse: Grounded answer payload with citations.

        Raises:
            AssistantError: If retrieval or response synthesis fails.
        """
        if not query.strip():
            raise AssistantError(
                message="User query cannot be empty.",
                details={"session_id": session_id},
            )

        logger.info(
            f"Assistant RAG query [session={session_id[:8]}]: '{query[:50]}...'"
        )

        # 1. Query parsing
        parsed = QueryParser.parse(query)

        # 2. Semantic vector context retrieval
        try:
            hits = self._retrieval.retrieve_context(
                parsed, meeting_id=meeting_id, top_k=top_k, min_score=min_score
            )
        except Exception as exc:
            logger.error(f"Context retrieval failed for RAG query: {exc}")
            raise AssistantError(
                message=f"Context retrieval failed: {exc}",
                details={"session_id": session_id, "query": query},
            ) from exc

        # Empty retrieval fallback (anti-hallucination)
        if not hits:
            fallback_answer = (
                "The provided meeting context does not contain information "
                "to answer this question."
            )
            logger.info(
                f"No vector hits retrieved for query '{query}'; returning fallback."
            )
            self._memory.add_turn(session_id, query, fallback_answer)
            return AssistantResponse(
                session_id=session_id,
                query=query,
                answer=fallback_answer,
                citations=[],
                retrieved_count=0,
                model_name=self._llm.model_id,
            )

        # 3. Grounded context construction ([Ref N] markers)
        grounded = ContextBuilder.build_grounded_context(hits)

        # 4. Dialogue history
        history_text = self._memory.format_history_text(session_id)

        # 5. Prompt construction
        system_prompt, user_prompt = AssistantPromptBuilder.build_prompt(
            question=query,
            context_text=grounded.context_text,
            history_text=history_text,
        )

        # 6. LLM response generation
        try:
            completion = self._llm.generate(
                user_prompt, system=system_prompt, max_tokens=self._max_tokens
            )
        except Exception as exc:
            logger.error(f"LLM generation failed for RAG query: {exc}")
            raise AssistantError(
                message=f"LLM answer generation failed: {exc}",
                details={"session_id": session_id, "query": query},
            ) from exc

        # 7. Response parsing and citation extraction
        response = ResponseGenerator.generate_response(
            session_id=session_id,
            query=query,
            raw_completion=completion,
            available_citations=grounded.citations,
            model_name=self._llm.model_id,
        )

        # 8. Record turn in conversation memory
        self._memory.add_turn(session_id, query, response.answer)

        logger.info(
            f"Assistant RAG response generated [session={session_id[:8]}, "
            f"citations={len(response.citations)}]"
        )
        return response
