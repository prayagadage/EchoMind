"""Prompt builder assembling transcript context into LLM prompts."""

from modules.storage.models import SpeakerModel, TranscriptModel

# Valid item types for the JSON schema embedded in the prompt
VALID_TYPES = [
    "ACTION_ITEM",
    "DECISION",
    "DEADLINE",
    "QUESTION",
    "RISK",
    "FOLLOW_UP",
]

SYSTEM_PROMPT = """You are a meeting intelligence extractor.
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


def build_extraction_prompt(
    transcripts: list[TranscriptModel],
    speakers: dict[str, SpeakerModel] | None = None,
) -> tuple[str, str]:
    """Build system and user prompts for intelligence extraction.

    Args:
        transcripts: Ordered list of transcript segments.
        speakers: Optional speaker_id → SpeakerModel lookup.

    Returns:
        Tuple of (system_prompt, user_prompt).
    """
    if not transcripts:
        return SYSTEM_PROMPT, "No transcript content available."

    speaker_map = speakers or {}
    lines: list[str] = []

    for t in transcripts:
        name = _resolve_speaker_name(t.speaker_id, speaker_map)
        ts = f"{t.timestamp:.1f}s"
        lang = t.language.upper()
        text = t.translated_text or t.original_text
        lines.append(f"[{ts}] {name} ({lang}): {text}")

    user_prompt = "Meeting Transcript:\n\n" + "\n".join(lines)
    return SYSTEM_PROMPT, user_prompt


def _resolve_speaker_name(
    speaker_id: str | None,
    speaker_map: dict[str, SpeakerModel],
) -> str:
    """Resolve speaker display name from ID.

    Args:
        speaker_id: Speaker UUID or None.
        speaker_map: Lookup dictionary.

    Returns:
        str: Display name, temporary name, or 'Unknown'.
    """
    if not speaker_id:
        return "Unknown"
    spk = speaker_map.get(speaker_id)
    if not spk:
        return "Unknown"
    return spk.display_name or spk.temporary_name
