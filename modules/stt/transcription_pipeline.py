"""TranscriptionPipeline orchestrator for real-time streaming speech recognition.

Subscribes to AudioChunk events on EventBus (without modifying Audio Engine),
filters silence via VoiceActivityDetector, runs MLXWhisperEngine inference,
and publishes TranscriptEvent payloads to EventBus.
"""

import threading
import time

import numpy as np
from core.event_bus import EventBus
from loguru import logger

from modules.audio.models import AudioChunk
from modules.stt.transcript_event import TranscriptEvent
from modules.stt.vad import VoiceActivityDetector
from modules.stt.whisper_engine import MLXWhisperEngine


class TranscriptionPipeline:
    """Real-time streaming speech recognition pipeline."""

    def __init__(
        self,
        event_bus: EventBus | None = None,
        whisper_engine: MLXWhisperEngine | None = None,
        vad: VoiceActivityDetector | None = None,
        max_segment_sec: float = 5.0,
        silence_timeout_sec: float = 0.8,
    ) -> None:
        """Initialize TranscriptionPipeline instance.

        Args:
            event_bus: EventBus for subscribing/publishing events.
            whisper_engine: MLXWhisperEngine instance.
            vad: VoiceActivityDetector instance.
            max_segment_sec: Max audio duration before forcing STT.
            silence_timeout_sec: Silence duration following speech to flush segment.
        """
        self._event_bus = event_bus or EventBus()
        self._whisper_engine = whisper_engine or MLXWhisperEngine()
        self._vad = vad or VoiceActivityDetector()

        self._max_segment_sec = max_segment_sec
        self._silence_timeout_sec = silence_timeout_sec

        self._speech_frames: list[np.ndarray] = []
        self._start_timestamp: float = 0.0
        self._last_speech_timestamp: float = 0.0
        self._sequence_counter: int = 0
        self._running: bool = False
        self._lock = threading.Lock()

        logger.debug("TranscriptionPipeline initialized.")

    def start(self) -> None:
        """Subscribe pipeline to AudioChunk events on EventBus."""
        with self._lock:
            if self._running:
                return
            self._event_bus.subscribe(AudioChunk, self.on_audio_chunk)
            self._running = True
            logger.info(
                "TranscriptionPipeline STARTED & subscribed to AudioChunk events."
            )

    def stop(self) -> None:
        """Unsubscribe pipeline and flush remaining buffered audio."""
        with self._lock:
            if not self._running:
                return
            self._event_bus.unsubscribe(AudioChunk, self.on_audio_chunk)
            self._running = False
            logger.info("TranscriptionPipeline STOPPED.")

        # Flush any remaining speech frames
        self._process_accumulated_segment(is_final=True)

    def on_audio_chunk(self, chunk: AudioChunk) -> None:
        """Subscriber handler receiving real-time AudioChunk payloads.

        Args:
            chunk: AudioChunk instance emitted by AudioEngine.
        """
        if not self._running:
            return

        is_speech, confidence = self._vad.is_speech(chunk.data, chunk.sample_rate)

        with self._lock:
            now = time.time()

            if is_speech:
                if not self._speech_frames:
                    self._start_timestamp = chunk.timestamp
                self._speech_frames.append(chunk.data)
                self._last_speech_timestamp = now

                # Calculate accumulated speech duration
                total_samples = sum(len(f) for f in self._speech_frames)
                accumulated_sec = total_samples / chunk.sample_rate

                if accumulated_sec >= self._max_segment_sec:
                    logger.debug(
                        "Max segment duration reached; triggering STT inference."
                    )
                    self._process_accumulated_segment_in_lock(chunk.sample_rate)

            else:
                # Silence detected
                if self._speech_frames:
                    silence_duration = now - self._last_speech_timestamp
                    if silence_duration >= self._silence_timeout_sec:
                        logger.debug(
                            f"Silence timeout ({silence_duration:.2f}s) reached; "
                            "flushing speech segment."
                        )
                        self._process_accumulated_segment_in_lock(chunk.sample_rate)

    def _process_accumulated_segment_in_lock(
        self, sample_rate: int = 16000, is_final: bool = True
    ) -> None:
        """Internal helper flushing accumulated speech frames under lock."""
        if not self._speech_frames:
            return

        frames_to_process = list(self._speech_frames)
        start_time = self._start_timestamp
        end_time = time.time()

        # Clear buffer state
        self._speech_frames.clear()

        # Concatenate audio frames
        audio_array = np.concatenate(frames_to_process)
        self._sequence_counter += 1
        seq_num = self._sequence_counter

        # Dispatch inference
        self._run_inference_and_publish(
            audio_array, sample_rate, start_time, end_time, seq_num, is_final
        )

    def _process_accumulated_segment(self, is_final: bool = True) -> None:
        """Public thread-safe flush method."""
        with self._lock:
            self._process_accumulated_segment_in_lock(is_final=is_final)

    def _run_inference_and_publish(
        self,
        audio_array: np.ndarray,
        sample_rate: int,
        start_time: float,
        end_time: float,
        sequence_number: int,
        is_final: bool,
    ) -> None:
        """Execute STT inference and publish TranscriptEvent to EventBus."""
        try:
            text, lang, confidence = self._whisper_engine.transcribe(
                audio_array, sample_rate
            )

            if not text:
                return

            event = TranscriptEvent(
                text=text,
                language=lang,
                start_time=start_time,
                end_time=end_time,
                confidence=confidence,
                is_final=is_final,
                sequence_number=sequence_number,
            )

            logger.info(
                f"Transcript #{event.sequence_number:03d} [{event.language.upper()}]: "
                f"'{event.text}'"
            )

            self._event_bus.publish(event)

        except Exception as exc:
            logger.error(f"Failed to process transcript segment: {exc}", exc_info=True)
