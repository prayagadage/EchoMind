"""Audio Engine Package for EchoMind.

Provides low-latency continuous microphone capture, in-memory ring buffering,
device discovery, and decoupled event streaming.
"""

from modules.audio.buffer import AudioBuffer
from modules.audio.device import AudioDeviceManager
from modules.audio.engine import AudioEngine, EngineState
from modules.audio.models import AudioChunk, AudioDeviceInfo

__all__ = [
    "AudioEngine",
    "EngineState",
    "AudioDeviceManager",
    "AudioBuffer",
    "AudioChunk",
    "AudioDeviceInfo",
]
