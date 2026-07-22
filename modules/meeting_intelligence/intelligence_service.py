"""Meeting Intelligence Service orchestrating extraction pipeline.

Supports incremental extraction during live meetings and a final
reconciliation pass at meeting end. Both modes share the same
pipeline: prompt_builder → LLM → parser → repository.
"""

import time

from core.event_bus import EventBus
from core.exceptions import EchoMindBaseException
from core.llm.provider import LLMProvider
from loguru import logger
from sqlalchemy.orm import Session

from modules.meeting_intelligence.events import IntelligenceExtractedEvent
from modules.meeting_intelligence.models import (
    IntelligenceItemModel,
    compute_content_hash,
)
from modules.meeting_intelligence.parser import extract_via_provider
from modules.meeting_intelligence.prompt_builder import build_extraction_prompt
from modules.meeting_intelligence.repository import IntelligenceRepository
from modules.storage.db import DatabaseEngine
from modules.storage.models import SpeakerModel, TranscriptModel
from modules.storage.repositories import SpeakerRepository, TranscriptRepository


class IntelligenceError(EchoMindBaseException):
    """Raised when intelligence extraction fails."""

    pass


class IntelligenceService:
    """Orchestrates meeting intelligence extraction.

    Supports two execution modes:
    - Incremental: processes new transcripts since last extraction
    - Final: reconciles all transcripts at meeting end
    """

    def __init__(
        self,
        llm: LLMProvider,
        db_engine: DatabaseEngine,
        event_bus: EventBus,
        max_tokens: int = 2048,
    ) -> None:
        """Initialize IntelligenceService.

        Args:
            llm: LLM provider for text generation.
            db_engine: Database engine for persistence.
            event_bus: EventBus for publishing events.
            max_tokens: Maximum tokens for LLM generation.
        """
        self._llm = llm
        self._db = db_engine
        self._bus = event_bus
        self._max_tokens = max_tokens
        # Track last processed sequence per meeting
        self._last_seq: dict[str, int] = {}
        logger.debug("IntelligenceService initialized.")

    def extract_incremental(self, meeting_id: str, window_size: int = 20) -> int:
        """Extract intelligence from new transcripts since last call.

        Args:
            meeting_id: Target meeting UUID.
            window_size: Min transcript count to trigger extraction.

        Returns:
            int: Number of new items extracted.
        """
        last_seq = self._last_seq.get(meeting_id, -1)

        with self._db.session_scope() as session:
            all_transcripts = TranscriptRepository.get_by_meeting(session, meeting_id)
            new_transcripts = [
                t for t in all_transcripts if t.sequence_number > last_seq
            ]

            if len(new_transcripts) < window_size:
                return 0

            speakers = self._load_speakers(session, meeting_id)

        return self._run_extraction(
            meeting_id, new_transcripts, speakers, is_final=False
        )

    def extract_final(self, meeting_id: str) -> int:
        """Final reconciliation pass using all meeting transcripts.

        Deletes incremental items and re-extracts from full context
        to improve quality, merge duplicates, and refine deadlines.

        Args:
            meeting_id: Target meeting UUID.

        Returns:
            int: Number of final items extracted.
        """
        with self._db.session_scope() as session:
            # Delete non-final incremental items
            deleted = IntelligenceRepository.delete_non_final(session, meeting_id)
            if deleted:
                logger.info(
                    f"Reconciliation: removed {deleted} "
                    f"incremental items for meeting {meeting_id[:8]}"
                )

        with self._db.session_scope() as session:
            transcripts = TranscriptRepository.get_by_meeting(session, meeting_id)
            speakers = self._load_speakers(session, meeting_id)

        if not transcripts:
            logger.debug(
                f"No transcripts for meeting {meeting_id[:8]}, "
                "skipping final extraction."
            )
            return 0

        return self._run_extraction(meeting_id, transcripts, speakers, is_final=True)

    def _run_extraction(
        self,
        meeting_id: str,
        transcripts: list[TranscriptModel],
        speakers: dict[str, SpeakerModel],
        is_final: bool,
    ) -> int:
        """Core extraction pipeline shared by incremental and final.

        Args:
            meeting_id: Target meeting UUID.
            transcripts: Transcript segments to process.
            speakers: Speaker lookup dictionary.
            is_final: Whether this is the final reconciliation pass.

        Returns:
            int: Number of items persisted.
        """
        if not transcripts:
            return 0

        # Build prompt
        system_prompt, user_prompt = build_extraction_prompt(transcripts, speakers)

        # Call LLM
        try:
            parsed_items = extract_via_provider(
                self._llm,
                system_prompt,
                user_prompt,
                max_tokens=self._max_tokens,
            )
        except Exception as exc:
            logger.error(f"LLM extraction failed: {exc}")
            raise IntelligenceError(
                message=f"Intelligence extraction failed: {exc}",
                details={"meeting_id": meeting_id},
            ) from exc

        if not parsed_items:
            logger.debug(f"No items extracted for meeting {meeting_id[:8]}")
            return 0

        # Persist with dedup
        count = 0
        item_types: set[str] = set()

        with self._db.session_scope() as session:
            for item in parsed_items:
                content_hash = compute_content_hash(item.type, item.content)

                # Skip duplicates
                if IntelligenceRepository.exists_by_hash(
                    session, meeting_id, item.type, content_hash
                ):
                    logger.debug(
                        f"Skipping duplicate: {item.type} " f"hash={content_hash}"
                    )
                    continue

                model = IntelligenceItemModel(
                    meeting_id=meeting_id,
                    item_type=item.type,
                    content=item.content,
                    content_hash=content_hash,
                    assignee=item.assignee,
                    due_date=item.due_date,
                    priority=item.priority,
                    confidence=item.confidence,
                    source_text=item.source_text,
                    is_final=1 if is_final else 0,
                )
                IntelligenceRepository.create(session, model)
                count += 1
                item_types.add(item.type)

        # Update tracking
        if transcripts:
            max_seq = max(t.sequence_number for t in transcripts)
            self._last_seq[meeting_id] = max_seq

        # Publish event
        mode = "final" if is_final else "incremental"
        logger.info(f"Extracted {count} {mode} items for " f"meeting {meeting_id[:8]}")

        self._bus.publish(
            IntelligenceExtractedEvent(
                meeting_id=meeting_id,
                item_count=count,
                item_types=sorted(item_types),
                is_final=is_final,
                timestamp=time.time(),
            )
        )

        return count

    @staticmethod
    def _load_speakers(
        session: Session,
        meeting_id: str,
    ) -> dict[str, SpeakerModel]:
        """Load speaker lookup dictionary for a meeting.

        Args:
            session: Active SQLAlchemy session.
            meeting_id: Target meeting UUID.

        Returns:
            dict mapping speaker_id to SpeakerModel.
        """
        speakers = SpeakerRepository.get_by_meeting(session, meeting_id)
        return {s.id: s for s in speakers}
