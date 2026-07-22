"""Prompt builder assembling QA system prompt, dialogue history, and context blocks."""

from core.llm.prompts.qa import (
    QA_SYSTEM_PROMPT as SYSTEM_PROMPT,
)
from core.llm.prompts.qa import (
    build_qa_user_prompt,
)


class AssistantPromptBuilder:
    """Assembles complete LLM system and user prompts for RAG Q&A."""

    @staticmethod
    def build_prompt(
        question: str,
        context_text: str,
        history_text: str = "",
    ) -> tuple[str, str]:
        """Build system and user prompts for RAG generation.

        Args:
            question: User natural language question.
            context_text: Formatted [Ref N] context text string.
            history_text: Optional multi-turn conversation history.

        Returns:
            tuple[str, str]: Tuple of (system_prompt, user_prompt).
        """
        user_prompt = build_qa_user_prompt(
            question=question,
            context_text=context_text,
            history_text=history_text,
        )
        return SYSTEM_PROMPT, user_prompt
