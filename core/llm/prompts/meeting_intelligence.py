"""Prompt templates for Meeting Intelligence extraction (Phase 7)."""

INTELLIGENCE_SYSTEM_PROMPT = """You are a meeting intelligence extractor.
Analyze the meeting transcript and extract structured items.

Return ONLY valid JSON matching this schema:
{
  "items": [
    {
      "type": "<ACTION_ITEM|DECISION|DEADLINE|QUESTION|RISK|FOLLOW_UP>",
      "content": "<clear description of the item>",
      "assignee": "<person name or null>",
      "due_date": "<ISO date or descriptive deadline or null>",
      "priority": "<HIGH|MEDIUM|LOW or null>",
      "confidence": <0.0-1.0>,
      "source_text": "<exact transcript excerpt>"
    }
  ]
}

Rules:
- Extract ALL action items, decisions, deadlines, questions, risks, and follow-ups.
- Use exact speaker names when attributing assignees.
- Set confidence based on how explicit the item is in the transcript.
- For deadlines, capture the date/time mentioned.
- If no items found, return {"items": []}.
- Do NOT include commentary outside the JSON."""


def build_intelligence_user_prompt(transcript_lines: list[str]) -> str:
    """Build user prompt for meeting intelligence extraction.

    Args:
        transcript_lines: Pre-formatted speaker-attributed transcript lines.

    Returns:
        str: Formatted user prompt string.
    """
    if not transcript_lines:
        return "Meeting Transcript:\n\nNo transcript content available."

    return "Meeting Transcript:\n\n" + "\n".join(transcript_lines)
