"""Response parser validating LLM JSON output against Pydantic schemas."""

from core.llm.provider import LLMProvider, generate_json
from loguru import logger

from modules.meeting_intelligence.models import (
    IntelligenceResponse,
    ItemType,
    ParsedItem,
)

# ponytail: valid types as a set for O(1) lookup
_VALID_TYPES = {t.value for t in ItemType}


def parse_llm_response(raw: str) -> list[ParsedItem]:
    """Parse raw LLM text into validated intelligence items.

    Handles malformed JSON, missing fields, and invalid types
    gracefully — returns whatever valid items can be salvaged.

    Args:
        raw: Raw LLM response string.

    Returns:
        List of validated ParsedItem instances.
    """
    try:
        import json

        from core.llm.provider import _extract_json
        from pydantic import ValidationError

        json_str = _extract_json(raw)
        data = json.loads(json_str)
        response = IntelligenceResponse.model_validate(data)
    except (ValueError, json.JSONDecodeError, ValidationError) as exc:
        logger.warning(f"Failed to parse LLM response: {exc}")
        return []

    # Filter to valid item types
    valid: list[ParsedItem] = []
    for item in response.items:
        normalized = item.type.upper().replace(" ", "_")
        if normalized in _VALID_TYPES:
            valid.append(
                ParsedItem(
                    type=normalized,
                    content=item.content,
                    assignee=item.assignee,
                    due_date=item.due_date,
                    priority=item.priority,
                    confidence=item.confidence,
                    source_text=item.source_text,
                )
            )
        else:
            logger.debug(f"Skipping unknown item type: {item.type}")

    return valid


def extract_via_provider(
    provider: LLMProvider,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 2048,
) -> list[ParsedItem]:
    """Extract intelligence items using generate_json.

    Falls back to raw parsing if generate_json raises.

    Args:
        provider: LLM inference backend.
        system_prompt: System prompt string.
        user_prompt: User prompt with transcript content.
        max_tokens: Maximum tokens to generate.

    Returns:
        List of validated ParsedItem instances.
    """
    try:
        response = generate_json(
            provider,
            user_prompt,
            schema=IntelligenceResponse,
            system=system_prompt,
            max_tokens=max_tokens,
        )
        # Filter to valid types
        valid: list[ParsedItem] = []
        for item in response.items:
            normalized = item.type.upper().replace(" ", "_")
            if normalized in _VALID_TYPES:
                valid.append(
                    ParsedItem(
                        type=normalized,
                        content=item.content,
                        assignee=item.assignee,
                        due_date=item.due_date,
                        priority=item.priority,
                        confidence=item.confidence,
                        source_text=item.source_text,
                    )
                )
        return valid
    except ValueError:
        logger.warning("generate_json failed, attempting raw parse")
        raw = provider.generate(
            user_prompt, system=system_prompt, max_tokens=max_tokens
        )
        return parse_llm_response(raw)
