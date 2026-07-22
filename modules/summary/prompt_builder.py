"""Prompt builder formatting SummaryContext into system and user prompts."""

from core.llm.prompts.summarization import (
    SUMMARIZATION_SYSTEM_PROMPT as SYSTEM_PROMPT,
)
from core.llm.prompts.summarization import (
    build_summarization_user_prompt,
)

from modules.summary.summary_builder import SummaryContext


def build_summary_prompt(context: SummaryContext) -> tuple[str, str]:
    """Build system and user prompts for summary generation.

    Args:
        context: SummaryContext instance.

    Returns:
        tuple[str, str]: Tuple of (system_prompt, user_prompt).
    """
    speakers_text = context.format_speakers_text()
    intelligence_text = context.format_intelligence_text()
    transcript_text = context.format_transcript_text()

    user_prompt = build_summarization_user_prompt(
        meeting_title=context.title,
        speakers_text=speakers_text,
        intelligence_text=intelligence_text,
        transcript_text=transcript_text,
    )

    return SYSTEM_PROMPT, user_prompt
