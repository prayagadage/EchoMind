"""LLM provider protocol defining the inference interface.

Any backend (MLX, Ollama, OpenAI) implements this protocol
to be injectable into intelligence services.
"""

import json
from typing import Any, Protocol, TypeVar, runtime_checkable

from loguru import logger
from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


@runtime_checkable
class LLMProvider(Protocol):
    """Protocol for local or remote LLM inference backends."""

    def generate(
        self,
        prompt: str,
        *,
        system: str = "",
        max_tokens: int = 2048,
    ) -> str:
        """Generate a text completion.

        Args:
            prompt: User prompt string.
            system: Optional system prompt.
            max_tokens: Maximum tokens to generate.

        Returns:
            str: Raw generated text.
        """
        ...

    @property
    def model_id(self) -> str:
        """Return the model identifier string."""
        ...


def generate_json(
    provider: LLMProvider,
    prompt: str,
    *,
    schema: type[T],
    system: str = "",
    max_tokens: int = 2048,
) -> T:
    """Generate structured JSON output validated against a Pydantic schema.

    Calls the provider, extracts JSON from the response,
    and validates it against the given schema.

    Args:
        provider: LLM inference backend.
        prompt: User prompt string.
        schema: Pydantic model class for validation.
        system: Optional system prompt.
        max_tokens: Maximum tokens to generate.

    Returns:
        Validated Pydantic model instance.

    Raises:
        ValueError: If JSON extraction or validation fails.
    """
    raw = provider.generate(prompt, system=system, max_tokens=max_tokens)
    json_str = _extract_json(raw)

    try:
        data: Any = json.loads(json_str)
    except json.JSONDecodeError as exc:
        logger.warning(f"LLM returned invalid JSON: {exc}")
        raise ValueError(f"Malformed JSON from LLM: {exc}") from exc

    try:
        return schema.model_validate(data)
    except ValidationError as exc:
        logger.warning(f"LLM JSON failed schema validation: {exc}")
        raise ValueError(f"Schema validation failed: {exc}") from exc


def _extract_json(text: str) -> str:
    """Extract JSON from LLM output that may contain markdown fences.

    Args:
        text: Raw LLM response string.

    Returns:
        str: Extracted JSON string.
    """
    stripped = text.strip()

    # Strip ```json ... ``` fences
    if stripped.startswith("```"):
        lines = stripped.split("\n")
        # Remove first line (```json) and last line (```)
        inner_lines = []
        started = False
        for line in lines:
            if not started:
                started = True
                continue
            if line.strip() == "```":
                break
            inner_lines.append(line)
        return "\n".join(inner_lines)

    # Find first { or [ to last } or ]
    start_obj = stripped.find("{")
    start_arr = stripped.find("[")

    if start_obj == -1 and start_arr == -1:
        return stripped

    if start_arr == -1 or (start_obj != -1 and start_obj < start_arr):
        start = start_obj
        end = stripped.rfind("}") + 1
    else:
        start = start_arr
        end = stripped.rfind("]") + 1

    if end <= start:
        return stripped

    return stripped[start:end]
