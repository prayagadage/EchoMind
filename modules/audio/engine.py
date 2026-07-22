"""Core AudioEngine for low-latency continuous microphone capture.

Manages sounddevice InputStream callbacks, state machine (STOPPED, RUNNING, PAUSED),
in-memory ring buffer updates, and publishing AudioChunk events via EventBus.
"""

import threading
import time
from enum import Enum, auto
from typing import Any

import numpy as np
import sounddevice as sd
from core.config import Settings, get_settings
from core.event_bus import EventBus
from core.exceptions import AudioEngineError
from loguru import logger

from modules.audio.buffer import AudioBuffer
from modules.audio.device import AudioDeviceManager
from modules.audio.models import AudioChunk, AudioDeviceInfo


class EngineState(Enum):
    """Lifecycle states for the AudioEngine state machine."""

    STOPPED = auto()
    RUNNING = auto()
    PAUSED = auto()


class AudioEngine:
    """Low-latency continuous macOS audio capture engine.

    Streams microphone input into NumPy float32 arrays, updates an in-memory
    AudioBuffer ring buffer, and publishes AudioChunk instances over the EventBus.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        event_bus: EventBus | None = None,
        buffer_duration_sec: float = 30.0,
    ) -> None:
        """Initialize AudioEngine instance.

        Args:
            settings: Configuration settings (defaults to global cached).
            event_bus: EventBus for publishing AudioChunk events.
            buffer_duration_sec: Seconds of recent audio retained in memory.
        """
        self._settings = settings or get_settings()
        self._event_bus = event_bus or EventBus()
        self._sample_rate = self._settings.audio_sample_rate
        self._channels = self._settings.audio_channels

        self._buffer = AudioBuffer(
            buffer_duration_sec=buffer_duration_sec,
            sample_rate=self._sample_rate,
            channels=self._channels,
        )

        self._state = EngineState.STOPPED
        self._stream: sd.InputStream | None = None
        self._active_device: AudioDeviceInfo | None = None
        self._sequence_counter = 0
        self._state_lock = threading.Lock()

        logger.debug(
            f"AudioEngine initialized: sample_rate={self._sample_rate}Hz, "
            f"channels={self._channels}, buffer={buffer_duration_sec}s"
        )

    @property
    def state(self) -> EngineState:
        """Access current state of AudioEngine state machine."""
        with self._state_lock:
            return self._state

    @property
    def active_device(self) -> AudioDeviceInfo | None:
        """Access active audio input hardware device information."""
        return self._active_device

    @property
    def buffer(self) -> AudioBuffer:
        """Access the underlying AudioBuffer ring buffer."""
        return self._buffer

    @property
    def event_bus(self) -> EventBus:
        """Access the associated EventBus instance."""
        return self._event_bus

    def start(self, device_spec: int | str | None = None) -> None:
        """Start continuous audio streaming from specified input device.

        Args:
            device_spec: Device ID, name substring, or None for default.

        Raises:
            AudioEngineError: If engine is already running or stream fails to start.
            AudioDeviceError: If specified device is invalid or disconnected.
        """
        with self._state_lock:
            if self._state != EngineState.STOPPED:
                raise AudioEngineError(
                    message=f"Cannot start from state '{self._state.name}'.",
                    details={"state": self._state.name},
                )

            # 1. Resolve and validate input device
            self._active_device = AudioDeviceManager.get_device_by_id_or_name(
                device_spec
            )
            logger.info(
                f"Starting AudioEngine on device '{self._active_device.name}' "
                f"(ID: {self._active_device.device_id}, Rate: {self._sample_rate}Hz)"
            )

            # 2. Block size calculation (chunk duration in samples)
            block_size = int(self._settings.audio_chunk_sec * self._sample_rate)

            try:
                self._stream = sd.InputStream(
                    device=self._active_device.device_id,
                    channels=self._channels,
                    samplerate=self._sample_rate,
                    blocksize=block_size,
                    dtype=np.float32,
                    callback=self._audio_callback,
                )
                self._stream.start()
                self._state = EngineState.RUNNING
                self._sequence_counter = 0
                logger.info("AudioEngine continuous capture stream STARTED.")
            except Exception as exc:
                self._state = EngineState.STOPPED
                self._stream = None
                raise AudioEngineError(
                    message=f"Failed to start sounddevice audio stream: {exc}",
                    details={"device": self._active_device.name, "error": str(exc)},
                ) from exc

    def pause(self) -> None:
        """Pause audio capture stream processing."""
        with self._state_lock:
            if self._state != EngineState.RUNNING:
                logger.warning(
                    f"Pause requested but AudioEngine state is '{self._state.name}'."
                )
                return
            self._state = EngineState.PAUSED
            logger.info("AudioEngine capture stream PAUSED.")

    def resume(self) -> None:
        """Resume audio capture stream processing from PAUSED state."""
        with self._state_lock:
            if self._state != EngineState.PAUSED:
                logger.warning(
                    f"Resume requested but AudioEngine state is '{self._state.name}'."
                )
                return
            self._state = EngineState.RUNNING
            logger.info("AudioEngine capture stream RESUMED.")

    def stop(self) -> None:
        """Stop audio capture stream and release CoreAudio resources."""
        with self._state_lock:
            if self._state == EngineState.STOPPED:
                return

            logger.info("Stopping AudioEngine capture stream...")
            if self._stream is not None:
                try:
                    self._stream.stop()
                    self._stream.close()
                except Exception as exc:
                    logger.warning(f"Error while closing sounddevice stream: {exc}")
                finally:
                    self._stream = None

            self._state = EngineState.STOPPED
            logger.info("AudioEngine capture stream STOPPED.")

    def _audio_callback(
        self,
        indata: np.ndarray,
        frames: int,
        time_info: Any,
        status: sd.CallbackFlags,
    ) -> None:
        """Real-time sounddevice audio callback.

        Runs on native CoreAudio driver thread. Must remain low-latency.
        """
        if status:
            logger.warning(f"CoreAudio stream callback status flag: {status}")

        with self._state_lock:
            current_state = self._state

        if current_state != EngineState.RUNNING:
            return

        # 1. Copy raw PCM data to prevent driver buffer reuse mutation
        data_copy = indata.squeeze().copy()

        # 2. Encapsulate into AudioChunk
        self._sequence_counter += 1
        chunk = AudioChunk(
            data=data_copy,
            timestamp=time.time(),
            sample_rate=self._sample_rate,
            channels=self._channels,
            sequence_number=self._sequence_counter,
        )

        # 3. Write into memory-only ring buffer
        self._buffer.write(chunk)

        # 4. Publish to EventBus for decoupled downstream subscribers
        self._event_bus.publish(chunk)
