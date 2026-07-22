import time

import numpy as np
import pytest
from core.event_bus import EventBus
from modules.audio.models import AudioChunk
from modules.speaker.speaker_events import (
    SpeakerAssignedEvent,
    SpeakerChangedEvent,
)
from modules.speaker.speaker_segmenter import SegmenterConfig, SpeakerSegmenter
from modules.speaker.speaker_service import SpeakerService
from modules.storage.db import DatabaseEngine
from modules.storage.models import SpeakerModel, TranscriptModel
from modules.storage.repositories import (
    MeetingRepository,
    SpeakerRepository,
    TranscriptRepository,
)
from modules.stt.transcript_event import LANG_ENGLISH, TranscriptEvent
from sqlalchemy import select


@pytest.fixture
def memory_db() -> DatabaseEngine:
    """Provide in-memory DatabaseEngine instance."""
    engine = DatabaseEngine(db_url="sqlite:///:memory:")
    engine.init_db()
    return engine


def generate_synth_speech(
    freq: float, duration_sec: float = 0.5, sr: int = 16000
) -> np.ndarray:
    """Generate synthetic speech signal with distinct spectral profile."""
    t = np.linspace(0, duration_sec, int(sr * duration_sec), endpoint=False)
    # Pitch modulation and harmonics to generate distinct spectral energy profiles
    signal = 0.6 * np.sin(2 * np.pi * freq * t) + 0.3 * np.cos(
        2 * np.pi * (freq * 3.5) * t
    )
    return signal.astype(np.float32)


def test_single_speaker_segmenter() -> None:
    """Verify SpeakerSegmenter handles single speaker continuously."""
    segmenter = SpeakerSegmenter()
    spk1_audio = generate_synth_speech(freq=220.0)

    # First chunk -> Speaker A
    res1 = segmenter.process_chunk(spk1_audio)
    assert res1.is_speaker_change is True
    assert res1.temporary_name == "Speaker A"

    # Second chunk -> Still Speaker A
    res2 = segmenter.process_chunk(spk1_audio)
    assert res2.is_speaker_change is False
    assert res2.temporary_name == "Speaker A"
    assert res2.speaker_id == res1.speaker_id


def test_alternating_speakers_continuity() -> None:
    """Verify segmenter tracks alternating speakers and maintains continuity."""
    segmenter = SpeakerSegmenter()
    spk1_audio = generate_synth_speech(freq=150.0)
    spk2_audio = generate_synth_speech(freq=3500.0)

    # Speaker 1 -> Speaker A
    res1 = segmenter.process_chunk(spk1_audio)
    assert res1.temporary_name == "Speaker A"

    # Speaker 2 -> Speaker B
    res2 = segmenter.process_chunk(spk2_audio)
    assert res2.is_speaker_change is True
    assert res2.temporary_name == "Speaker B"

    # Speaker 1 returns -> Reidentified as Speaker A
    res3 = segmenter.process_chunk(spk1_audio)
    assert res3.is_speaker_change is True
    assert res3.temporary_name == "Speaker A"
    assert res3.speaker_id == res1.speaker_id


def test_silence_and_background_noise() -> None:
    """Verify segmenter handles silence and low background noise gracefully."""
    config = SegmenterConfig(silence_rms_threshold=0.01)
    segmenter = SpeakerSegmenter(config=config)

    silence = np.zeros(8000, dtype=np.float32)
    noise = np.random.normal(0, 0.001, 8000).astype(np.float32)

    res_silence = segmenter.process_chunk(silence)
    assert res_silence.is_silence is True

    res_noise = segmenter.process_chunk(noise)
    assert res_noise.is_silence is True


def test_speaker_repository_crud(memory_db: DatabaseEngine) -> None:
    """Verify SpeakerRepository database operations."""
    with memory_db.session_scope() as session:
        m = MeetingRepository.create(session, "Speaker DB Test")
        m_id = m.id

        spk = SpeakerModel(
            meeting_id=m_id,
            temporary_name="Speaker A",
        )
        SpeakerRepository.create(session, spk)
        spk_id = spk.id

    with memory_db.session_scope() as session:
        fetched = SpeakerRepository.get_by_id(session, spk_id)
        assert fetched is not None
        assert fetched.temporary_name == "Speaker A"
        assert fetched.meeting_id == m_id

        all_spks = SpeakerRepository.get_by_meeting(session, m_id)
        assert len(all_spks) == 1


def test_speaker_service_worker_event_bus(memory_db: DatabaseEngine) -> None:
    """Verify SpeakerService processes audio, updates transcripts, and emits events."""
    bus = EventBus(max_workers=2)
    service = SpeakerService(event_bus=bus, db_engine=memory_db)
    service.start()

    with memory_db.session_scope() as session:
        m = MeetingRepository.create(session, "Speaker Event Test")
        m_id = m.id
        t_model = TranscriptModel(
            meeting_id=m_id,
            sequence_number=1,
            timestamp=0.0,
            language=LANG_ENGLISH,
            original_text="Testing speaker assignment.",
            confidence=0.95,
        )
        TranscriptRepository.add(session, t_model)
        t_id = t_model.id

    service.set_active_meeting(m_id)

    emitted_assigned: list[SpeakerAssignedEvent] = []
    emitted_changed: list[SpeakerChangedEvent] = []

    bus.subscribe(SpeakerAssignedEvent, lambda evt: emitted_assigned.append(evt))
    bus.subscribe(SpeakerChangedEvent, lambda evt: emitted_changed.append(evt))

    # Send audio chunk
    spk_audio = generate_synth_speech(freq=200.0)
    chunk = AudioChunk(
        data=spk_audio,
        sample_rate=16000,
        channels=1,
        timestamp=time.time(),
        sequence_number=1,
    )
    bus.publish(chunk)
    time.sleep(0.1)

    # Send TranscriptEvent matching sequence_number
    t_event = TranscriptEvent(
        text="Testing speaker assignment.",
        language=LANG_ENGLISH,
        start_time=0.0,
        end_time=2.0,
        confidence=0.95,
        is_final=True,
        sequence_number=1,
    )
    bus.publish(t_event)

    time.sleep(0.3)
    service.stop()
    bus.shutdown()

    assert len(emitted_changed) >= 1
    assert len(emitted_assigned) == 1
    assert emitted_assigned[0].transcript_id == t_id
    assert emitted_assigned[0].temporary_name == "Speaker A"

    # Verify transcript table in DB was updated with speaker_id

    with memory_db.session_scope() as session:
        updated_t = session.scalar(
            select(TranscriptModel).where(TranscriptModel.id == t_id)
        )
        assert updated_t is not None
        assert updated_t.speaker_id == emitted_assigned[0].speaker_id
