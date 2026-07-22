"""Prompt templates for Interactive QA Engine (Future phase)."""

QA_SYSTEM_PROMPT = """You are EchoMind Q&A Assistant.
Answer questions using ONLY the provided meeting transcripts and intelligence context.

Rules:
- Be direct, accurate, and concise.
- If the context does not contain enough information to answer, state that clearly."""


def build_qa_user_prompt(question: str, context_text: str) -> str:
    """Build user prompt for meeting Q&A.

    Args:
        question: User query string.
        context_text: Formatted meeting transcript and intelligence context.

    Returns:
        str: Formatted user prompt.
    """
    return f"MEETING CONTEXT:\n{context_text}\n\nUSER QUESTION: {question}"
