"""Response generator parsing LLM output and attaching source citations."""

import re

from loguru import logger

from modules.assistant.models import AssistantResponse, Citation


class ResponseGenerator:
    """Parses LLM completions and maps citation tags to structured Citations."""

    @staticmethod
    def generate_response(
        session_id: str,
        query: str,
        raw_completion: str,
        available_citations: list[Citation],
        model_name: str,
    ) -> AssistantResponse:
        """Parse raw LLM completion and construct AssistantResponse with citations.

        Args:
            session_id: Conversation session identifier.
            query: User natural language question.
            raw_completion: Raw completion text from LLM.
            available_citations: List of available Citation objects for retrieved hits.
            model_name: Identifier string of LLM model.

        Returns:
            AssistantResponse: Response object with answer and citations.
        """
        answer_text = ResponseGenerator._clean_thought_preamble(raw_completion)
        matched_citations: list[Citation] = []

        if available_citations:
            # Look for explicit [Ref N] or Ref N references in LLM answer
            ref_matches = re.findall(r"Ref\s*(\d+)", answer_text, re.IGNORECASE)
            matched_indices = set()
            for m in ref_matches:
                try:
                    idx = int(m) - 1
                    if 0 <= idx < len(available_citations):
                        matched_indices.add(idx)
                except ValueError:
                    continue

            if matched_indices:
                matched_citations = [
                    available_citations[i] for i in sorted(matched_indices)
                ]
            else:
                # If LLM did not format [Ref N], attach top retrieved citations
                matched_citations = available_citations[:3]
                logger.debug(
                    "LLM answer contained no explicit [Ref N] tags; "
                    "attaching top retrieved citations."
                )

        return AssistantResponse(
            session_id=session_id,
            query=query,
            answer=answer_text,
            citations=matched_citations,
            retrieved_count=len(available_citations),
            model_name=model_name,
        )

    @staticmethod
    def _clean_thought_preamble(text: str) -> str:
        """Strip internal reasoning blocks, XML tags, and meta-commentary."""
        if not text:
            return ""

        # 1. Remove XML <think>...</think> blocks
        cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

        # 2. Filter out paragraphs starting with internal reasoning preambles
        meta_starters = (
            "okay, the user is asking",
            "let me look through",
            "let me check",
            "first, looking at",
            "putting this together",
            "so the answer should",
            "let's check the provided context",
        )

        paragraphs = [p.strip() for p in cleaned.split("\n\n") if p.strip()]
        filtered = []
        for p in paragraphs:
            p_lower = p.lower()
            if any(p_lower.startswith(starter) for starter in meta_starters):
                continue
            filtered.append(p)

        if filtered:
            return "\n\n".join(filtered)
        return cleaned
