"""Prompt templates for Translation Engine (Phase 4)."""

TRANSLATION_SYSTEM_PROMPT = """You are a technical translator.
Translate into fluent English while preserving technical terms and names.

Rules:
- Do NOT translate technical terms (e.g., Python, SQL, API, MLX, Whisper, EchoMind).
- Preserve proper names (e.g., Prayag, Rahul, Priya).
- Output ONLY the translated text."""


def build_translation_user_prompt(
    text: str, source_language: str, target_language: str = "en"
) -> str:
    """Build user prompt for text translation.

    Args:
        text: Raw input text string.
        source_language: Source ISO language code ('mr', 'hi').
        target_language: Target ISO language code ('en').

    Returns:
        str: Formatted user prompt.
    """
    return f"Source ({source_language}): {text}\nTarget ({target_language}):"
