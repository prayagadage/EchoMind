"""MLX-based Qwen provider for Apple Silicon inference.

Uses mlx-lm to run Qwen 3 4B (4-bit quantized) locally
on Metal/ANE for offline text generation.
"""

from typing import Any

from loguru import logger

DEFAULT_MODEL_ID = "mlx-community/Qwen3-4B-4bit"


class QwenMLXProvider:
    """LLM provider using mlx-lm for local Qwen inference."""

    def __init__(
        self,
        model_id: str = DEFAULT_MODEL_ID,
    ) -> None:
        """Initialize Qwen MLX provider.

        Args:
            model_id: HuggingFace model identifier for mlx-lm.
        """
        self._model_id = model_id
        self._model: Any = None
        self._tokenizer: Any = None
        logger.debug(f"QwenMLXProvider created: model={model_id}")

    @property
    def model_id(self) -> str:
        """Return the model identifier string."""
        return self._model_id

    def _ensure_loaded(self) -> None:
        """Lazy-load model and tokenizer on first use."""
        if self._model is not None:
            return

        from mlx_lm import load

        logger.info(f"Loading MLX model: {self._model_id}")
        self._model, self._tokenizer = load(self._model_id)  # type: ignore[misc]
        logger.info(f"Model loaded: {self._model_id}")

    def generate(
        self,
        prompt: str,
        *,
        system: str = "",
        max_tokens: int = 2048,
    ) -> str:
        """Generate a text completion using Qwen via mlx-lm.

        Args:
            prompt: User prompt string.
            system: Optional system prompt.
            max_tokens: Maximum tokens to generate.

        Returns:
            str: Generated text.
        """
        self._ensure_loaded()

        from mlx_lm import generate as mlx_generate

        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        # Apply chat template if tokenizer supports it
        if hasattr(self._tokenizer, "apply_chat_template"):
            formatted: str = self._tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )
        else:
            # Fallback: concatenate system + user
            formatted = f"{system}\n\n{prompt}" if system else prompt

        result: str = mlx_generate(
            self._model,
            self._tokenizer,
            prompt=formatted,
            max_tokens=max_tokens,
        )

        logger.debug(f"Generated {len(result)} chars (max_tokens={max_tokens})")
        return result
