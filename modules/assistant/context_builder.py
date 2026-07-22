"""ContextBuilder constructing [Ref N] tagged context blocks and Citation mappings."""

from dataclasses import dataclass

from modules.assistant.models import Citation
from modules.search.models import SearchResult


@dataclass
class GroundedContextPayload:
    """Dataclass holding formatted prompt context text and source Citations map."""

    context_text: str
    citations: list[Citation]


class ContextBuilder:
    """Formats retrieved SearchResult hits into grounded RAG prompt context."""

    @staticmethod
    def build_grounded_context(hits: list[SearchResult]) -> GroundedContextPayload:
        """Format retrieved search hits into [Ref N] context blocks and Citations.

        Args:
            hits: List of SearchResult objects.

        Returns:
            GroundedContextPayload: Formatted text and citation mapping.
        """
        if not hits:
            return GroundedContextPayload(
                context_text="No relevant meeting records retrieved.",
                citations=[],
            )

        context_lines: list[str] = []
        citations: list[Citation] = []

        for idx, hit in enumerate(hits, 1):
            ref_id = f"Ref {idx}"
            spk_str = f" Speaker: {hit.speaker_name} |" if hit.speaker_name else ""
            ts_str = (
                f" Time: {hit.timestamp:.1f}s |" if hit.timestamp is not None else ""
            )

            header = (
                f"[{ref_id}] Meeting: '{hit.meeting_title}' | "
                f"Type: {hit.entity_type} |{spk_str}{ts_str}"
            )
            block = f"{header}\nContent: {hit.content}"
            context_lines.append(block)

            citation = Citation(
                ref_id=ref_id,
                meeting_id=hit.meeting_id,
                meeting_title=hit.meeting_title,
                entity_type=hit.entity_type,
                source_id=hit.source_id,
                content_snippet=hit.content,
                speaker_name=hit.speaker_name,
                timestamp=hit.timestamp,
            )
            citations.append(citation)

        formatted_text = "\n\n".join(context_lines)
        return GroundedContextPayload(context_text=formatted_text, citations=citations)
