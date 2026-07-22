"""Prompt templates for AI Meeting Assistant (Phase 10)."""

QA_SYSTEM_PROMPT = """You are EchoMind AI Meeting Assistant.
Answer questions strictly using ONLY provided context tagged [Ref 1], [Ref 2].

Rules:
1. Base your answer STRICTLY on context references.
2. Every major statement MUST cite its source like [Ref 1], [Ref 2].
3. Do NOT invent facts or use external knowledge.
4. If context is insufficient, state:
   "The provided meeting context does not contain information to answer this question."
5. Provide ONLY your direct final answer. Do NOT output internal reasoning,
   thought process, preamble ("Okay, the user is asking..."), or meta-commentary.
6. Maintain a helpful and clear tone."""


def build_qa_user_prompt(
    question: str,
    context_text: str,
    history_text: str = "",
) -> str:
    """Build user prompt for RAG meeting Q&A.

    Args:
        question: User query string.
        context_text: Formatted [Ref N] meeting context string.
        history_text: Optional formatted multi-turn conversation history.

    Returns:
        str: Formatted user prompt for LLM generation.
    """
    sections = []
    if history_text:
        sections.append(f"CONVERSATION HISTORY:\n{history_text}")

    sections.append(
        "MEETING CONTEXT (GROUND TRUTH):\n"
        f"{context_text if context_text else 'No context retrieved.'}"
    )
    sections.append(f"CURRENT USER QUESTION:\n{question}")

    return "\n\n".join(sections)
