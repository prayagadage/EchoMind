"""SummaryService orchestrating live and final meeting summary generation."""

import json
import time

from core.event_bus import EventBus
from core.exceptions import SummarizationError
from core.llm.provider import LLMProvider
from loguru import logger

from modules.storage.db import DatabaseEngine
from modules.summary.events import SummaryGeneratedEvent
from modules.summary.models import MeetingSummaryModel, SummaryType
from modules.summary.parser import extract_summary_via_provider
from modules.summary.prompt_builder import build_summary_prompt
from modules.summary.repository import SummaryRepository
from modules.summary.summary_builder import SummaryBuilder


class SummaryService:
    """Orchestrates live, final, and regenerated meeting summaries."""

    def __init__(
        self,
        llm: LLMProvider,
        db_engine: DatabaseEngine,
        event_bus: EventBus,
        max_tokens: int = 2048,
    ) -> None:
        """Initialize SummaryService instance.

        Args:
            llm: LLM provider implementation.
            db_engine: Database engine for persistence.
            event_bus: EventBus for publishing events.
            max_tokens: Maximum token budget for LLM generation.
        """
        self._llm = llm
        self._db = db_engine
        self._bus = event_bus
        self._max_tokens = max_tokens
        logger.debug("SummaryService initialized.")

    def generate_live_summary(self, meeting_id: str) -> MeetingSummaryModel | None:
        """Generate a live (incremental/periodic) meeting summary.

        Args:
            meeting_id: Target meeting UUID string.

        Returns:
            MeetingSummaryModel | None: Saved summary entity or None if empty.
        """
        return self._generate_summary(
            meeting_id=meeting_id,
            is_final=False,
            summary_type=SummaryType.COMBINED.value,
        )

    def generate_final_summary(self, meeting_id: str) -> MeetingSummaryModel | None:
        """Generate automatic final meeting summary upon meeting end.

        Cleans up previous non-final summaries and performs a comprehensive pass.

        Args:
            meeting_id: Target meeting UUID string.

        Returns:
            MeetingSummaryModel | None: Final saved summary entity or None.
        """
        with self._db.session_scope() as session:
            deleted = SummaryRepository.delete_non_final(session, meeting_id)
            if deleted:
                logger.info(
                    f"Reconciliation: removed {deleted} "
                    f"non-final summaries for meeting {meeting_id[:8]}"
                )

        return self._generate_summary(
            meeting_id=meeting_id,
            is_final=True,
            summary_type=SummaryType.COMBINED.value,
        )

    def regenerate_summary(
        self, meeting_id: str, is_final: bool = True
    ) -> MeetingSummaryModel | None:
        """Force regeneration of meeting summary.

        Args:
            meeting_id: Target meeting UUID string.
            is_final: Whether regenerated summary is marked final.

        Returns:
            MeetingSummaryModel | None: Newly generated summary model.
        """
        with self._db.session_scope() as session:
            existing = SummaryRepository.get_latest(session, meeting_id)
            new_version = "1.1"
            if existing and existing.model_version:
                try:
                    ver_val = float(existing.model_version)
                    new_version = f"{ver_val + 0.1:.1f}"
                except ValueError:
                    new_version = "2.0"

        return self._generate_summary(
            meeting_id=meeting_id,
            is_final=is_final,
            summary_type=SummaryType.COMBINED.value,
            model_version=new_version,
        )

    def get_summary(
        self, meeting_id: str, summary_type: str | None = None
    ) -> MeetingSummaryModel | None:
        """Retrieve the latest summary for a meeting.

        Args:
            meeting_id: Target meeting UUID string.
            summary_type: Optional SummaryType string filter.

        Returns:
            MeetingSummaryModel | None: Latest summary entity or None.
        """
        with self._db.session_scope() as session:
            return SummaryRepository.get_latest(session, meeting_id, summary_type)

    def _generate_summary(
        self,
        meeting_id: str,
        is_final: bool,
        summary_type: str,
        model_version: str = "1.0",
    ) -> MeetingSummaryModel | None:
        """Core summarization pipeline.

        Args:
            meeting_id: Target meeting UUID string.
            is_final: Whether summary is final.
            summary_type: SummaryType string.
            model_version: Version identifier string.

        Returns:
            MeetingSummaryModel | None: Saved summary model or None.
        """
        with self._db.session_scope() as session:
            context = SummaryBuilder.build_context(session, meeting_id)

        if not context.transcripts and not context.intelligence_items:
            logger.debug(
                f"No transcripts or items for meeting {meeting_id[:8]}, "
                "skipping summary generation."
            )
            return None

        system_prompt, user_prompt = build_summary_prompt(context)

        try:
            parsed = extract_summary_via_provider(
                self._llm,
                system_prompt,
                user_prompt,
                max_tokens=self._max_tokens,
            )
        except Exception as exc:
            logger.error(f"LLM summary generation failed: {exc}")
            raise SummarizationError(
                message=f"Failed to generate summary: {exc}",
                details={"meeting_id": meeting_id},
            ) from exc

        model = MeetingSummaryModel(
            meeting_id=meeting_id,
            summary_type=summary_type,
            executive_summary=parsed.executive_summary,
            bullet_points=json.dumps(parsed.bullet_points),
            key_takeaways=json.dumps(parsed.key_takeaways),
            model_name=self._llm.model_id,
            model_version=model_version,
            is_final=1 if is_final else 0,
        )

        with self._db.session_scope() as session:
            saved = SummaryRepository.create(session, model)
            saved_id = saved.id

        mode = "Final" if is_final else "Live"
        logger.info(
            f"Generated {mode} Summary (ID: {saved_id[:8]}) "
            f"for Meeting {meeting_id[:8]}"
        )

        self._bus.publish(
            SummaryGeneratedEvent(
                meeting_id=meeting_id,
                summary_id=saved_id,
                summary_type=summary_type,
                is_final=is_final,
                timestamp=time.time(),
            )
        )

        with self._db.session_scope() as session:
            return session.get(MeetingSummaryModel, saved_id)
