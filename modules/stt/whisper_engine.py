"""MLX Whisper Speech-to-Text inference engine for Apple Silicon.

Leverages mlx_whisper for fast on-device Metal/ANE accelerated inference,
automatic language detection (Marathi, Hindi, English), and offline execution.
"""

import numpy as np
from core.exceptions import STTInferenceError
from loguru import logger


class MLXWhisperEngine:
    """Offline Speech-to-Text engine powered by Apple Silicon MLX Whisper."""

    def __init__(
        self,
        model_name: str = "mlx-community/whisper-small-mlx",
        fallback_language: str = "en",
        language: str | None = None,
    ) -> None:
        """Initialize MLX Whisper inference engine.

        Args:
            model_name: MLX model repository name or path.
            fallback_language: Default language code if detection is ambiguous.
            language: Optional explicit language code (e.g., 'mr', 'hi', 'en').
        """
        self._model_name = model_name
        self._fallback_language = fallback_language
        self._language = language
        self._model_loaded = False
        logger.debug(
            f"MLXWhisperEngine initialized: model='{model_name}', language='{language}'"
        )

    def _ensure_model_loaded(self) -> None:
        """Lazy loader verifying mlx_whisper availability."""
        if self._model_loaded:
            return
        try:
            import mlx_whisper  # noqa: F401

            self._model_loaded = True
            logger.info(f"MLX Whisper engine ready using model '{self._model_name}'.")
        except ImportError as exc:
            logger.warning(f"mlx_whisper package import unavailable: {exc}")
            raise STTInferenceError(
                message="mlx_whisper package is not installed.",
                details={"error": str(exc)},
            ) from exc

    def transcribe(
        self,
        audio_data: np.ndarray,
        sample_rate: int = 16000,
        language: str | None = None,
    ) -> tuple[str, str, float]:
        """Transcribe PCM float32 audio array with auto or explicit language detection.

        Args:
            audio_data: 1D float32 NumPy array at 16000Hz.
            sample_rate: Sampling frequency in Hz.
            language: Explicit language code override (e.g. 'mr', 'hi', 'en').

        Returns:
            tuple[str, str, float]: (text, detected_language_code, confidence).

        Raises:
            STTInferenceError: If STT inference execution encounters an error.
        """
        if audio_data.size == 0:
            return "", self._fallback_language, 0.0

        data = audio_data.squeeze()

        try:
            import mlx_whisper

            target_lang = language or self._language
            kwargs: dict[str, str] = {}
            if target_lang and target_lang.lower() != "auto":
                kwargs["language"] = target_lang.lower()

            # Execute MLX Whisper STT
            result = mlx_whisper.transcribe(
                data,
                path_or_hf_repo=self._model_name,
                verbose=False,
                **kwargs,
            )

            text = str(result.get("text", "")).strip()
            detected_lang = str(result.get("language", self._fallback_language))

            # Filter out known Whisper hallucinations on quiet or noisy audio
            if self._is_hallucination(text):
                logger.debug(f"Filtered Whisper hallucination: '{text}'")
                return "", detected_lang.lower(), 0.0

            # Normalize language code (e.g. 'mr', 'hi', 'en')
            detected_lang_code = detected_lang.lower()

            logger.debug(
                f"MLX Whisper transcribed {len(data)/sample_rate:.2f}s -> "
                f"[{detected_lang_code.upper()}]: '{text}'"
            )
            return text, detected_lang_code, 0.95
        except Exception as exc:
            logger.error(f"MLX Whisper inference error: {exc}")
            raise STTInferenceError(
                message=f"Failed to transcribe audio segment: {exc}",
                details={"error": str(exc)},
            ) from exc

    def _is_hallucination(self, text: str) -> bool:
        """Check if transcribed text is a known Whisper hallucination pattern."""
        if not text:
            return True

        clean = text.strip()

        # 1. Repeated digits/punctuation (e.g., "1,2,3,4,5,5,5,5,5,5,5...")
        import re
        from collections import Counter

        if re.match(r"^[\d\s,.-]+$", clean) and len(clean) > 8:
            return True

        # 2. Excessive single digit repetitions
        digits = re.findall(r"\b\d+\b", clean)
        if len(digits) > 5 and (len(set(digits)) <= 2 or digits.count("5") > 4):
            return True

        # 3. Known subtitle/closing hallucination phrases
        lowered = clean.lower()
        phrases = [
            "subtitles by",
            "thanks for watching",
            "thank you for watching",
            "subscribe to my channel",
            "amara.org",
            "you for watching",
            "bye bye",
            "peace out",
        ]
        if any(p in lowered for p in phrases):
            return True

        # 4. Repeated consecutive word patterns (e.g. "siebie siebie", "आणि आणि")
        if re.search(r"(\b\w+\b)(?:\s*[,.]?\s*\1){2,}", clean, re.IGNORECASE):
            return True

        # 5. High frequency single word dominance (e.g. word > 35% of tokens)
        tokens = re.findall(r"\w+", clean)
        if len(tokens) >= 4:
            counts = Counter(tokens)
            _, highest_freq = counts.most_common(1)[0]
            if highest_freq >= 3 and (highest_freq / len(tokens)) > 0.35:
                return True

        # 6. Repetitive Devanagari/Latin zero symbols (e.g. ००००००००००)
        if re.search(r"[०0]{4,}", clean):
            return True

        return False
