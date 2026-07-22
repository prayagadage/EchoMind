"""Data structures and models for the Audio Engine."""

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class AudioChunk:
    """Immutable encapsulated raw PCM audio chunk frame.

    Attributes:
        data: Monophonic or multichannel float32 NumPy PCM array [-1.0, 1.0].
        timestamp: Unix Epoch timestamp in seconds when the chunk was recorded.
        sample_rate: Audio sampling frequency in Hz (e.g. 16000).
        channels: Channel count (1=Mono, 2=Stereo).
        sequence_number: Sequential index of the audio chunk.
    """

    data: np.ndarray
    timestamp: float
    sample_rate: int
    channels: int
    sequence_number: int

    @property
    def duration_sec(self) -> float:
        """Compute duration of audio chunk in seconds."""
        if self.sample_rate <= 0:
            return 0.0
        return float(len(self.data) / self.sample_rate)

    @property
    def rms_power(self) -> float:
        """Compute Root Mean Square (RMS) signal level (0.0 to 1.0)."""
        if self.data.size == 0:
            return 0.0
        return float(np.sqrt(np.mean(np.square(self.data))))


@dataclass(frozen=True)
class AudioDeviceInfo:
    """Description of an audio input hardware device.

    Attributes:
        device_id: CoreAudio device index.
        name: Name of the input device (e.g. 'MacBook Air Microphone').
        max_input_channels: Maximum input channels supported.
        default_sample_rate: Native sampling rate supported by hardware.
        is_default: True if this device is the default macOS input microphone.
    """

    device_id: int
    name: str
    max_input_channels: int
    default_sample_rate: float
    is_default: bool
