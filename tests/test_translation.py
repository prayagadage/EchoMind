"""Unit tests for Phase 4 Translation Engine & Event Architecture."""

import time

import pytest
from core.event_bus import EventBus
from modules.storage.db import DatabaseEngine
from modules.storage.models import TranscriptModel, TranslationModel
from modules.storage.repositories import TranscriptRepository, TranslationRepository
from modules.storage.service import TranscriptService
from modules.stt.transcript_event import (
    LANG_ENGLISH,
    LANG_HINDI,
    LANG_MARATHI,
    TranscriptEvent,
)
from modules.translation.engine import TranslationEngine
from modules.translation.service import TranslationService
from modules.translation.translation_event import TranslationEvent


@pytest.fixture
def memory_db() -> DatabaseEngine:
    """Provide in-memory DatabaseEngine instance."""
    engine = DatabaseEngine(db_url="sqlite:///:memory:")
    engine.init_db()
    return engine


def test_translation_event_properties() -> None:
    """Verify TranslationEvent properties."""
    evt = TranslationEvent(
        transcript_id="t-123",
        meeting_id="m-456",
        sequence_number=1,
        source_language=LANG_MARATHI,
        target_language="en",
        original_text="Shubh prabhat",
        translated_text="Good morning.",
        model_name="nmt-local-v1",
        timestamp=1000.0,
    )
    assert evt.transcript_id == "t-123"
    assert evt.source_language == "mr"
    assert evt.translated_text == "Good morning."


def test_translation_engine_skips_english() -> None:
    """Verify TranslationEngine skips translating English text."""
    engine = TranslationEngine()
    text, model = engine.translate("Hello EchoMind team", source_language=LANG_ENGLISH)
    assert text == "Hello EchoMind team"
    assert model == "none"


def test_translation_engine_marathi_hindi_translation() -> None:
    """Verify TranslationEngine translates Marathi and Hindi phrases."""
    engine = TranslationEngine()

    mr_text, _ = engine.translate("Kasa ahes?", source_language=LANG_MARATHI)
    assert mr_text == "How are you?"

    hi_text, _ = engine.translate(
        "Namaste, aap kaise hain?", source_language=LANG_HINDI
    )
    assert hi_text == "Hello, how are you?"


def test_translation_engine_preserves_technical_terms() -> None:
    """Verify TranslationEngine preserves technical terms and author names."""
    engine = TranslationEngine()

    text, _ = engine.translate(
        "Aajcha vishay Prayag ne design keleli Python API ahe.",
        source_language=LANG_MARATHI,
    )
    assert "Prayag" in text
    assert "Python" in text
    assert "API" in text


def test_translation_repository_crud(memory_db: DatabaseEngine) -> None:
    """Verify TranslationRepository persistence and retrieval."""
    with memory_db.session_scope() as session:
        t_model = TranscriptModel(
            meeting_id="m-1",
            sequence_number=1,
            timestamp=100.0,
            language=LANG_MARATHI,
            original_text="Shubh prabhat",
            confidence=0.9,
        )
        saved_t = TranscriptRepository.add(session, t_model)
        t_id = saved_t.id

        trans_model = TranslationModel(
            transcript_id=t_id,
            target_language="en",
            translated_text="Good morning.",
            model_name="nmt-local-v1",
        )
        TranslationRepository.create(session, trans_model)

    with memory_db.session_scope() as session:
        retrieved = TranslationRepository.get_by_transcript_id(session, t_id)
        assert retrieved is not None
        assert retrieved.translated_text == "Good morning."
        assert retrieved.target_language == "en"


def test_translation_service_worker_event_bus(memory_db: DatabaseEngine) -> None:
    """Verify TranslationService worker consumes and emits events."""
    bus = EventBus(max_workers=2)

    # 1. Initialize TranscriptService & TranslationService
    transcript_service = TranscriptService(db_engine=memory_db, event_bus=bus)
    translation_service = TranslationService(db_engine=memory_db, event_bus=bus)

    translation_service.start()

    transcript_service.start_meeting("Translation EventBus Test")
    emitted_translations: list[TranslationEvent] = []

    def on_translation(evt: TranslationEvent) -> None:
        emitted_translations.append(evt)

    bus.subscribe(TranslationEvent, on_translation)

    # 2. Emit Marathi TranscriptEvent onto EventBus
    stt_event = TranscriptEvent(
        text="Kasa ahes?",
        language=LANG_MARATHI,
        start_time=100.0,
        end_time=102.0,
        confidence=0.95,
        is_final=True,
        sequence_number=1,
    )
    bus.publish(stt_event)

    time.sleep(0.3)

    translation_service.stop()
    bus.shutdown()

    assert len(emitted_translations) == 1
    assert emitted_translations[0].translated_text == "How are you?"
    assert emitted_translations[0].source_language == "mr"
