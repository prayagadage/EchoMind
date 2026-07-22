"""Streaming Speaker Segmentation Engine extracting acoustic features."""

import uuid
from dataclasses import dataclass

import numpy as np
from loguru import logger


@dataclass
class SegmenterConfig:
    """Configurable thresholds for streaming speaker segmentation."""

    speaker_change_threshold: float = 0.35
    minimum_segment_duration: float = 0.8
    merge_gap_duration: float = 0.5
    silence_padding: float = 0.3
    reidentification_threshold: float = 0.30
    silence_rms_threshold: float = 0.005


@dataclass
class SegmentResult:
    """Result of processing an audio chunk for speaker boundary detection."""

    speaker_id: str
    temporary_name: str
    is_speaker_change: bool
    confidence: float
    is_silence: bool = False


class SpeakerSegmenter:
    """Real-time speaker segmenter using acoustic feature clustering."""

    def __init__(self, config: SegmenterConfig | None = None) -> None:
        """Initialize SpeakerSegmenter instance.

        Args:
            config: SegmenterConfig instance or None for defaults.
        """
        self._config = config or SegmenterConfig()
        self._speaker_centroids: dict[str, np.ndarray] = {}
        self._speaker_names: dict[str, str] = {}
        self._speaker_counts: dict[str, int] = {}
        self._active_speaker_id: str | None = None
        self._next_speaker_letter_index = 0

        logger.debug("SpeakerSegmenter initialized with custom thresholds.")

    def reset(self) -> None:
        """Reset segmenter state for a new meeting session."""
        self._speaker_centroids.clear()
        self._speaker_names.clear()
        self._speaker_counts.clear()
        self._active_speaker_id = None
        self._next_speaker_letter_index = 0
        logger.debug("SpeakerSegmenter state reset.")

    def process_chunk(
        self, samples: np.ndarray, sample_rate: int = 16000
    ) -> SegmentResult:
        """Process streaming audio samples and return speaker segmentation result.

        Args:
            samples: Float32 audio samples array.
            sample_rate: Sample rate in Hz (default 16000).

        Returns:
            SegmentResult: Identified speaker ID, temporary label, and change flag.
        """
        if samples is None or len(samples) == 0:
            active_id = self._active_speaker_id or "speaker-1"
            name = self._speaker_names.get(active_id, "Speaker A")
            return SegmentResult(
                speaker_id=active_id,
                temporary_name=name,
                is_speaker_change=False,
                confidence=0.5,
                is_silence=True,
            )

        # 1. Check for silence using RMS energy contour
        rms = float(np.sqrt(np.mean(np.square(samples))))
        if rms < self._config.silence_rms_threshold:
            active_id = self._active_speaker_id or "speaker-1"
            name = self._speaker_names.get(active_id, "Speaker A")
            return SegmentResult(
                speaker_id=active_id,
                temporary_name=name,
                is_speaker_change=False,
                confidence=0.5,
                is_silence=True,
            )

        # 2. Extract 16-dimensional acoustic feature vector
        features = self._extract_acoustic_features(samples, sample_rate)

        # 3. Handle initial meeting speaker
        if not self._speaker_centroids:
            spk_id, spk_name = self._create_new_speaker(features)
            self._active_speaker_id = spk_id
            return SegmentResult(
                speaker_id=spk_id,
                temporary_name=spk_name,
                is_speaker_change=True,
                confidence=1.0,
            )

        # 4. Compare feature vector against active speaker centroid
        assert self._active_speaker_id is not None
        active_centroid = self._speaker_centroids[self._active_speaker_id]
        active_dist = self._cosine_distance(features, active_centroid)

        # If chunk is close to active speaker, update centroid and return
        if active_dist <= self._config.speaker_change_threshold:
            self._update_speaker_centroid(self._active_speaker_id, features)
            name = self._speaker_names[self._active_speaker_id]
            conf = float(max(0.0, 1.0 - active_dist))
            return SegmentResult(
                speaker_id=self._active_speaker_id,
                temporary_name=name,
                is_speaker_change=False,
                confidence=conf,
            )

        # 5. Check if chunk matches another existing speaker (Continuity Tracking)
        best_speaker_id = None
        min_dist = float("inf")

        for spk_id, centroid in self._speaker_centroids.items():
            dist = self._cosine_distance(features, centroid)
            if dist < min_dist:
                min_dist = dist
                best_speaker_id = spk_id

        if (
            best_speaker_id is not None
            and min_dist <= self._config.reidentification_threshold
        ):
            # Reuse existing historical speaker in meeting session
            prev_active = self._active_speaker_id
            self._active_speaker_id = best_speaker_id
            self._update_speaker_centroid(best_speaker_id, features)
            name = self._speaker_names[best_speaker_id]
            is_change = best_speaker_id != prev_active
            conf = float(max(0.0, 1.0 - min_dist))

            if is_change:
                d_val = min_dist
                logger.info(
                    f"Speaker changed -> Reidentified {name} (dist: {d_val:.3f})"
                )

            return SegmentResult(
                speaker_id=best_speaker_id,
                temporary_name=name,
                is_speaker_change=is_change,
                confidence=conf,
            )

        # 6. Distance exceeds threshold -> Assign new Speaker ID
        spk_id, spk_name = self._create_new_speaker(features)
        self._active_speaker_id = spk_id
        logger.info(f"Speaker changed -> Assigned new {spk_name} (ID: {spk_id[:8]})")

        return SegmentResult(
            speaker_id=spk_id,
            temporary_name=spk_name,
            is_speaker_change=True,
            confidence=0.9,
        )

    def _extract_acoustic_features(
        self, samples: np.ndarray, sample_rate: int
    ) -> np.ndarray:
        """Extract 16D normalized acoustic feature vector from audio samples."""
        # 1. RMS Energy
        rms = float(np.sqrt(np.mean(np.square(samples))))

        # 2. Zero Crossing Rate
        zcr = float(np.mean(np.abs(np.diff(np.signbit(samples)))))

        # 3. FFT Magnitude Spectrum
        fft_mag = np.abs(np.fft.rfft(samples))
        freqs = np.fft.rfftfreq(len(samples), 1.0 / sample_rate)

        # 4. Spectral Centroid
        tot_mag = float(np.sum(fft_mag)) + 1e-9
        centroid = float(np.sum(freqs * fft_mag) / tot_mag)

        # 5. 12-bin Mel Frequency Log Energies
        mel_bins = 12
        split_mags = np.array_split(fft_mag, mel_bins)
        mel_energies = [
            float(np.log(np.mean(b**2) + 1e-9)) for b in split_mags if len(b) > 0
        ]
        while len(mel_energies) < mel_bins:
            mel_energies.append(0.0)

        # Combine into 16D feature vector
        vec = np.array(
            [rms, zcr, centroid / (sample_rate / 2.0)] + mel_energies[:mel_bins],
            dtype=np.float32,
        )
        norm = float(np.linalg.norm(vec)) + 1e-9
        return vec / norm

    def _cosine_distance(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Compute cosine distance between two normalized feature vectors."""
        dot = float(np.dot(vec1, vec2))
        norm1 = float(np.linalg.norm(vec1)) + 1e-9
        norm2 = float(np.linalg.norm(vec2)) + 1e-9
        cos_sim = dot / (norm1 * norm2)
        return float(1.0 - np.clip(cos_sim, -1.0, 1.0))

    def _create_new_speaker(self, initial_features: np.ndarray) -> tuple[str, str]:
        """Create and register a new temporary speaker entity."""
        spk_id = str(uuid.uuid4())
        letter = chr(ord("A") + self._next_speaker_letter_index)
        temp_name = f"Speaker {letter}"
        self._next_speaker_letter_index += 1

        self._speaker_centroids[spk_id] = initial_features.copy()
        self._speaker_names[spk_id] = temp_name
        self._speaker_counts[spk_id] = 1

        return spk_id, temp_name

    def _update_speaker_centroid(
        self, speaker_id: str, new_features: np.ndarray
    ) -> None:
        """Update running acoustic centroid for active speaker."""
        if speaker_id not in self._speaker_centroids:
            return
        n = self._speaker_counts[speaker_id]
        curr = self._speaker_centroids[speaker_id]
        updated = (curr * n + new_features) / (n + 1)
        norm = float(np.linalg.norm(updated)) + 1e-9
        self._speaker_centroids[speaker_id] = updated / norm
        self._speaker_counts[speaker_id] = n + 1
