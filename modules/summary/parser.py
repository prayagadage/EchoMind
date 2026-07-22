"""Summary response parser validating LLM completions into schemas."""

import json

from core.llm.provider import LLMProvider, _extract_json, generate_json
from loguru import logger
from pydantic import ValidationError

from modules.summary.models import SummaryResponseSchema


def parse_summary_response(raw: str) -> SummaryResponseSchema:
    """Parse raw LLM response text into validated SummaryResponseSchema.

    Args:
        raw: Raw LLM completion string.

    Returns:
        SummaryResponseSchema: Validated summary payload or fallback default.
    """
    try:
        json_str = _extract_json(raw)
        data = json.loads(json_str)
        return SummaryResponseSchema.model_validate(data)
    except (ValueError, json.JSONDecodeError, ValidationError) as exc:
        logger.warning(f"Failed to parse LLM summary response: {exc}")
        # Fallback: wrap raw text in executive summary
        return SummaryResponseSchema(
            executive_summary=raw.strip() if raw else "Summary unavailable.",
            bullet_points=[],
            key_takeaways=[],
        )


def extract_summary_via_provider(
    provider: LLMProvider,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 2048,
) -> SummaryResponseSchema:
    """Extract summary output via LLM provider using structured JSON generation.

    Args:
        provider: Active LLM inference provider.
        system_prompt: System prompt instructions.
        user_prompt: User context prompt.
        max_tokens: Maximum completion token budget.

    Returns:
        SummaryResponseSchema: Validated summary structure.
    """
    try:
        return generate_json(
            provider,
            user_prompt,
            schema=SummaryResponseSchema,
            system=system_prompt,
            max_tokens=max_tokens,
        )
    except ValueError:
        logger.warning("generate_json failed for summary, attempting raw parse")
        raw = provider.generate(
            user_prompt, system=system_prompt, max_tokens=max_tokens
        )
        return parse_summary_response(raw)
