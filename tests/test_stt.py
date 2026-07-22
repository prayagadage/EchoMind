"""Unit tests for Phase 2 Speech Recognition (STT) package."""

from unittest.mock import MagicMock, patch

import numpy as np
from core.event_bus import EventBus
from modules.audio.models import AudioChunk
from modules.stt.transcript_event import (
    LANG_ENGLISH,
    LANG_MARATHI,
    TranscriptEvent,
)
from modules.stt.transcript_formatter import TranscriptFormatter
from modules.stt.transcription_pipeline import TranscriptionPipeline
from modules.stt.vad import VoiceActivityDetector
from modules.stt.whisper_engine import MLXWhisperEngine


def test_transcript_event_properties() -> None:
    """Verify TranscriptEvent properties and duration calculation."""
    event = TranscriptEvent(
        text="Namaste, how are you?",
        language=LANG_ENGLISH,
        start_time=100.0,
        end_time=102.5,
        confidence=0.95,
        is_final=True,
        sequence_number=1,
    )

    assert event.duration_sec == 2.5
    assert event.language_label == "English"
    assert event.text == "Namaste, how are you?"


def test_vad_silence_vs_speech() -> None:
    """Verify VoiceActivityDetector distinguishes between silence and active speech."""
    vad = VoiceActivityDetector(energy_threshold=0.01)

    # 1. Silence / zeros array
    silence = np.zeros(16000, dtype=np.float32)
    is_speech, conf = vad.is_speech(silence)
    assert not is_speech
    assert conf < 0.1

    # 2. Active speech / high RMS array
    speech = np.full(16000, 0.1, dtype=np.float32)
    is_speech, conf = vad.is_speech(speech)
    assert is_speech
    assert conf > 0.5


def test_whisper_engine_transcribe_mock() -> None:
    """Verify MLXWhisperEngine handles inference response via mock."""
    mock_response = {"text": "   Kasa ahes?   ", "language": "mr"}

    with patch("mlx_whisper.transcribe", return_value=mock_response):
        engine = MLXWhisperEngine()
        data = np.full(16000, 0.05, dtype=np.float32)
        text, lang, conf = engine.transcribe(data)

        assert text == "Kasa ahes?"
        assert lang == "mr"
        assert conf > 0.9


def test_transcription_pipeline_accumulation_and_publish() -> None:
    """Verify TranscriptionPipeline accumulates speech frames and publishes events."""
    bus = EventBus(max_workers=2)
    mock_whisper = MagicMock()
    mock_whisper.transcribe.return_value = ("Hello EchoMind", "en", 0.98)

    mock_vad = MagicMock()
    mock_vad.is_speech.return_value = (True, 0.9)

    pipeline = TranscriptionPipeline(
        event_bus=bus,
        whisper_engine=mock_whisper,
        vad=mock_vad,
        max_segment_sec=0.2,  # Short threshold to trigger fast publish
    )

    published_events: list[TranscriptEvent] = []

    def mock_subscriber(event: TranscriptEvent) -> None:
        published_events.append(event)

    bus.subscribe(TranscriptEvent, mock_subscriber)
    pipeline.start()

    # Emit two active speech AudioChunks
    chunk1 = AudioChunk(
        data=np.full(1600, 0.05, dtype=np.float32),
        timestamp=100.0,
        sample_rate=16000,
        channels=1,
        sequence_number=1,
    )
    chunk2 = AudioChunk(
        data=np.full(1600, 0.05, dtype=np.float32),
        timestamp=100.1,
        sample_rate=16000,
        channels=1,
        sequence_number=2,
    )

    bus.publish(chunk1)
    bus.publish(chunk2)

    import time

    time.sleep(0.2)

    pipeline.stop()
    bus.shutdown()

    assert len(published_events) >= 1
    assert published_events[0].text == "Hello EchoMind"
    assert published_events[0].language == "en"


def test_transcript_formatter() -> None:
    """Verify console and JSON formatting routines."""
    event = TranscriptEvent(
        text="Shubh Prabhat",
        language=LANG_MARATHI,
        start_time=1000.0,
        end_time=1003.0,
        confidence=0.92,
        is_final=True,
        sequence_number=5,
    )

    console_str = TranscriptFormatter.format_console(event)
    assert "Shubh Prabhat" in console_str
    assert "Marathi" in console_str

    json_dict = TranscriptFormatter.format_json(event)
    assert json_dict["text"] == "Shubh Prabhat"
    assert json_dict["language"] == "mr"
    assert json_dict["duration_sec"] == 3.0
