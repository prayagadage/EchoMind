"""Comprehensive unit tests for the Audio Engine and EventBus."""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from core.config import Settings
from core.event_bus import EventBus
from core.exceptions import AudioEngineError
from modules.audio.buffer import AudioBuffer
from modules.audio.device import AudioDeviceManager
from modules.audio.engine import AudioEngine, EngineState
from modules.audio.models import AudioChunk, AudioDeviceInfo


def test_audio_chunk_properties() -> None:
    """Verify AudioChunk duration and RMS power calculation."""
    sample_rate = 16000
    data = np.full(16000, 0.5, dtype=np.float32)
    chunk = AudioChunk(
        data=data,
        timestamp=1000.0,
        sample_rate=sample_rate,
        channels=1,
        sequence_number=1,
    )

    assert chunk.duration_sec == 1.0
    assert pytest.approx(chunk.rms_power, 0.01) == 0.5


def test_audio_buffer_write_and_read() -> None:
    """Verify writing to and reading recent audio from AudioBuffer."""
    buffer = AudioBuffer(buffer_duration_sec=2.0, sample_rate=100, channels=1)
    assert buffer.capacity_samples == 200

    data = np.ones(50, dtype=np.float32)
    chunk = AudioChunk(
        data=data,
        timestamp=100.0,
        sample_rate=100,
        channels=1,
        sequence_number=1,
    )
    buffer.write(chunk)

    assert buffer.total_samples_written == 50
    assert buffer.current_duration_sec == 0.5

    recent = buffer.get_recent_audio(0.5)
    assert len(recent) == 50
    assert np.all(recent == 1.0)


def test_audio_buffer_wrap_around() -> None:
    """Verify circular overwrite behavior when writing beyond capacity."""
    buffer = AudioBuffer(buffer_duration_sec=1.0, sample_rate=10, channels=1)

    # Fill buffer with 10 samples of 1.0
    c1 = AudioChunk(
        data=np.ones(10, dtype=np.float32),
        timestamp=1.0,
        sample_rate=10,
        channels=1,
        sequence_number=1,
    )
    buffer.write(c1)

    # Overwrite with 5 samples of 2.0
    c2 = AudioChunk(
        data=np.full(5, 2.0, dtype=np.float32),
        timestamp=2.0,
        sample_rate=10,
        channels=1,
        sequence_number=2,
    )
    buffer.write(c2)

    recent = buffer.get_recent_audio(1.0)
    assert len(recent) == 10
    # First 5 samples should be 1.0, last 5 samples should be 2.0
    assert np.array_equal(recent[:5], np.ones(5, dtype=np.float32))
    assert np.array_equal(recent[5:], np.full(5, 2.0, dtype=np.float32))


def test_event_bus_subscription_and_dispatch() -> None:
    """Verify EventBus handler registration and event dispatching."""
    bus = EventBus(max_workers=2)
    received: list[AudioChunk] = []

    def mock_handler(chunk: AudioChunk) -> None:
        received.append(chunk)

    bus.subscribe(AudioChunk, mock_handler)

    chunk = AudioChunk(
        data=np.zeros(10, dtype=np.float32),
        timestamp=1.0,
        sample_rate=16000,
        channels=1,
        sequence_number=1,
    )
    bus.publish(chunk)

    # Wait briefly for worker thread pool execution
    import time

    time.sleep(0.1)

    assert len(received) == 1
    assert received[0].sequence_number == 1

    bus.unsubscribe(AudioChunk, mock_handler)
    bus.shutdown()


def test_audio_device_manager_query() -> None:
    """Verify AudioDeviceManager input device enumeration mock."""
    mock_devs = [
        {
            "name": "MacBook Air Microphone",
            "max_input_channels": 1,
            "default_samplerate": 44100.0,
        },
        {"name": "HDMI Output", "max_input_channels": 0, "default_samplerate": 48000.0},
    ]

    with (
        patch("sounddevice.query_devices", return_value=mock_devs),
        patch("sounddevice.default.device", [0, 1]),
    ):
        devices = AudioDeviceManager.list_input_devices()
        assert len(devices) == 1
        assert devices[0].name == "MacBook Air Microphone"
        assert devices[0].is_default


def test_audio_engine_state_transitions(mock_settings: Settings) -> None:
    """Verify AudioEngine state machine transitions (START, PAUSE, RESUME, STOP)."""
    mock_dev = AudioDeviceInfo(
        device_id=0,
        name="Test Mic",
        max_input_channels=1,
        default_sample_rate=16000.0,
        is_default=True,
    )

    with (
        patch.object(
            AudioDeviceManager, "get_device_by_id_or_name", return_value=mock_dev
        ),
        patch("sounddevice.InputStream") as mock_stream_cls,
    ):

        mock_stream = MagicMock()
        mock_stream_cls.return_value = mock_stream

        engine = AudioEngine(settings=mock_settings)
        assert engine.state == EngineState.STOPPED

        # 1. Start Engine
        engine.start(0)
        assert engine.state == EngineState.RUNNING
        assert mock_stream.start.called

        # Cannot start again while running
        with pytest.raises(AudioEngineError):
            engine.start(0)

        # 2. Pause Engine
        engine.pause()
        assert engine.state == EngineState.PAUSED

        # 3. Resume Engine
        engine.resume()
        assert engine.state == EngineState.RUNNING

        # 4. Stop Engine
        engine.stop()
        assert engine.state == EngineState.STOPPED
        assert mock_stream.stop.called
        assert mock_stream.close.called
