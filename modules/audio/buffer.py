"""Thread-safe circular in-memory ring buffer for audio PCM data.

Buffers recent configurable N seconds of raw float32 NumPy audio arrays.
Memory is pre-allocated on initialization to guarantee low latency.
No disk I/O or file saving occurs.
"""

import threading

import numpy as np
from loguru import logger

from modules.audio.models import AudioChunk


class AudioBuffer:
    """Pre-allocated circular ring buffer holding recent float32 audio arrays."""

    def __init__(
        self,
        buffer_duration_sec: float = 30.0,
        sample_rate: int = 16000,
        channels: int = 1,
    ) -> None:
        """Initialize circular audio ring buffer.

        Args:
            buffer_duration_sec: Max seconds of audio to retain in memory.
            sample_rate: Target audio sampling rate in Hz.
            channels: Audio channel count (1=Mono, 2=Stereo).
        """
        self._buffer_duration_sec = buffer_duration_sec
        self._sample_rate = sample_rate
        self._channels = channels
        self._max_samples = int(buffer_duration_sec * sample_rate)

        # Pre-allocate contiguous NumPy array memory
        self._buffer = np.zeros(self._max_samples, dtype=np.float32)
        self._write_index = 0
        self._filled_samples = 0
        self._total_samples_written = 0
        self._lock = threading.Lock()

        logger.debug(
            f"AudioBuffer initialized: capacity={self._max_samples} samples "
            f"({buffer_duration_sec}s at {sample_rate}Hz)"
        )

    @property
    def capacity_samples(self) -> int:
        """Return maximum sample capacity of buffer."""
        return self._max_samples

    @property
    def sample_rate(self) -> int:
        """Return buffer target sample rate."""
        return self._sample_rate

    @property
    def current_duration_sec(self) -> float:
        """Return duration in seconds of audio currently stored in buffer."""
        with self._lock:
            return float(self._filled_samples / self._sample_rate)

    @property
    def total_samples_written(self) -> int:
        """Return cumulative sample count written to buffer since initialization."""
        with self._lock:
            return self._total_samples_written

    def write(self, chunk: AudioChunk) -> None:
        """Write an AudioChunk's array payload into circular ring buffer.

        Args:
            chunk: AudioChunk instance containing raw float32 NumPy PCM array.
        """
        data = chunk.data
        if data.ndim > 1:
            data = data.squeeze()

        num_samples = len(data)
        if num_samples == 0:
            return

        with self._lock:
            if num_samples >= self._max_samples:
                # Chunk is larger than buffer capacity; store last max_samples
                self._buffer[:] = data[-self._max_samples :]
                self._write_index = 0
                self._filled_samples = self._max_samples
            else:
                end_index = self._write_index + num_samples
                if end_index <= self._max_samples:
                    self._buffer[self._write_index : end_index] = data
                else:
                    first_part = self._max_samples - self._write_index
                    second_part = num_samples - first_part
                    self._buffer[self._write_index :] = data[:first_part]
                    self._buffer[:second_part] = data[first_part:]

                self._write_index = (
                    self._write_index + num_samples
                ) % self._max_samples
                self._filled_samples = min(
                    self._max_samples, self._filled_samples + num_samples
                )

            self._total_samples_written += num_samples

    def get_recent_audio(self, duration_sec: float) -> np.ndarray:
        """Retrieve recent N seconds of audio as a contiguous float32 NumPy array.

        Args:
            duration_sec: Requested audio duration in seconds.

        Returns:
            np.ndarray: Contiguous 1D float32 array containing requested audio.
        """
        requested_samples = int(duration_sec * self._sample_rate)

        with self._lock:
            if self._filled_samples == 0 or requested_samples <= 0:
                return np.array([], dtype=np.float32)

            actual_samples = min(requested_samples, self._filled_samples)

            if self._filled_samples < self._max_samples:
                # Buffer has not wrapped around yet
                start_index = max(0, self._write_index - actual_samples)
                return self._buffer[start_index : self._write_index].copy()

            # Buffer has wrapped around
            start_index = (self._write_index - actual_samples) % self._max_samples
            if start_index < self._write_index:
                return self._buffer[start_index : self._write_index].copy()
            else:
                return np.concatenate(
                    (self._buffer[start_index:], self._buffer[: self._write_index])
                )

    def clear(self) -> None:
        """Reset buffer state and zero out stored samples."""
        with self._lock:
            self._buffer.fill(0)
            self._write_index = 0
            self._filled_samples = 0
            self._total_samples_written = 0
            logger.debug("AudioBuffer cleared.")
