"""Voice Activity Detection (VAD) module for silence filtering.

Prevents unnecessary ML model inference by discriminating between active human speech
and silent/ambient background noise using signal power and VAD thresholds.
"""

import numpy as np
from loguru import logger


class VoiceActivityDetector:
    """Voice Activity Detector evaluating audio PCM frames for active speech."""

    def __init__(
        self,
        energy_threshold: float = 0.008,
        min_speech_duration_sec: float = 0.3,
    ) -> None:
        """Initialize Voice Activity Detector.

        Args:
            energy_threshold: Minimum RMS signal power to classify as speech.
            min_speech_duration_sec: Minimum continuous speech window duration.
        """
        self._energy_threshold = energy_threshold
        self._min_speech_duration_sec = min_speech_duration_sec
        logger.debug(
            f"VoiceActivityDetector initialized: energy_threshold={energy_threshold}"
        )

    def is_speech(
        self, audio_data: np.ndarray, sample_rate: int = 16000
    ) -> tuple[bool, float]:
        """Evaluate if input audio array contains active human speech.

        Args:
            audio_data: 1D float32 NumPy PCM array normalized in [-1.0, 1.0].
            sample_rate: Audio sampling frequency in Hz.

        Returns:
            tuple[bool, float]: (is_speech_flag, confidence_score_0_to_1).
        """
        if audio_data.size == 0:
            return False, 0.0

        # Ensure monophonic 1D array
        data = audio_data.squeeze()
        if data.ndim > 1:
            data = np.mean(data, axis=1)

        # 1. Compute Root Mean Square (RMS) energy
        rms = float(np.sqrt(np.mean(np.square(data))))

        # 2. Compute Peak Amplitude ratio
        peak = float(np.max(np.abs(data)))

        # 3. Dynamic confidence scoring
        if rms < self._energy_threshold or peak < (self._energy_threshold * 1.5):
            return False, float(rms / max(self._energy_threshold, 1e-6))

        # Scaled confidence score capped at 1.0
        confidence = min(1.0, float(rms / (self._energy_threshold * 3.0)))
        return True, confidence
