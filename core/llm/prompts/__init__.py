"""Prompt engineering layer for EchoMind LLM services.

Provides versioned, reusable prompt templates for intelligence,
summarization, translation, and interactive QA services.
"""

from core.llm.prompts.meeting_intelligence import (
    INTELLIGENCE_SYSTEM_PROMPT,
    build_intelligence_user_prompt,
)
from core.llm.prompts.qa import QA_SYSTEM_PROMPT, build_qa_user_prompt
from core.llm.prompts.summarization import (
    SUMMARIZATION_SYSTEM_PROMPT,
    build_summarization_user_prompt,
)
from core.llm.prompts.translation import (
    TRANSLATION_SYSTEM_PROMPT,
    build_translation_user_prompt,
)

__all__ = [
    "INTELLIGENCE_SYSTEM_PROMPT",
    "QA_SYSTEM_PROMPT",
    "SUMMARIZATION_SYSTEM_PROMPT",
    "TRANSLATION_SYSTEM_PROMPT",
    "build_intelligence_user_prompt",
    "build_qa_user_prompt",
    "build_summarization_user_prompt",
    "build_translation_user_prompt",
]
