"""LLM provider abstraction for EchoMind.

Exposes a protocol interface and MLX-based Qwen implementation,
keeping intelligence modules independent of the inference backend.
"""

from core.llm.mlx_provider import QwenMLXProvider
from core.llm.provider import LLMProvider

__all__ = ["LLMProvider", "QwenMLXProvider"]
