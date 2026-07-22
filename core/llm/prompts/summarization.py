"""Prompt templates for Meeting Summarization Engine (Phase 8)."""

SUMMARIZATION_SYSTEM_PROMPT = """You are a senior executive meeting assistant.
Synthesize meeting context and transcripts into an accurate summary.

Return ONLY valid JSON matching this schema:
{
  "executive_summary": "<High-level 2-4 sentence narrative summary of the meeting.>",
  "bullet_points": [
    "<Key discussion point or decision 1>",
    "<Key discussion point or decision 2>"
  ],
  "key_takeaways": [
    "<Critical takeaway or strategic insight 1>",
    "<Critical takeaway or strategic insight 2>"
  ]
}

Rules:
- Base your summary STRICTLY on transcripts, dialogue, and intelligence.
- Do NOT invent facts or hallucinate details not present in context.
- Explicitly attribute major decisions and action items to named speakers.
- Ensure bullet points and key takeaways are concise and actionable.
- If context is minimal, state that there is insufficient dialogue.
- Return ONLY the JSON object."""


def build_summarization_user_prompt(
    meeting_title: str,
    speakers_text: str,
    intelligence_text: str,
    transcript_text: str,
) -> str:
    """Build user prompt for meeting summarization.

    Args:
        meeting_title: Title of the meeting session.
        speakers_text: Formatted string listing active speakers.
        intelligence_text: Formatted string of structured intelligence items.
        transcript_text: Formatted chronological transcript text.

    Returns:
        str: Formatted user prompt string.
    """
    transcript_clause = transcript_text if transcript_text else "No dialogue recorded."
    sections = [
        f"MEETING TITLE: {meeting_title}",
        f"ACTIVE SPEAKERS:\n{speakers_text if speakers_text else 'None'}",
        (
            "EXTRACTED STRUCTURED INTELLIGENCE (GROUND TRUTH):\n"
            f"{intelligence_text if intelligence_text else 'None'}"
        ),
        f"TRANSCRIPT DIALOGUE:\n{transcript_clause}",
    ]
    return "\n\n".join(sections)
