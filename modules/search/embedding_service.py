"""Embedding service interface and local semantic embedding provider.

Generates 384-dimensional normalized vector embeddings for local offline
semantic search without calling external APIs or LLM decoders.
"""

import re
from typing import Protocol, runtime_checkable

import numpy as np
from loguru import logger

EMBEDDING_DIM = 384


@runtime_checkable
class EmbeddingService(Protocol):
    """Protocol for embedding generation providers."""

    def embed_text(self, text: str) -> list[float]:
        """Generate a single normalized embedding vector for text.

        Args:
            text: Input text string.

        Returns:
            list[float]: Normalized embedding float array (length 384).
        """
        ...

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate normalized embedding vectors for a batch of texts.

        Args:
            texts: List of input text strings.

        Returns:
            list[list[float]]: List of normalized embedding float arrays.
        """
        ...

    @property
    def dimension(self) -> int:
        """Return the vector embedding dimension."""
        ...


class LocalSemanticEmbeddingProvider(EmbeddingService):
    """Fast offline local embedding provider producing 384-dim L2-normalized vectors."""

    def __init__(self, dimension: int = EMBEDDING_DIM) -> None:
        """Initialize LocalSemanticEmbeddingProvider.

        Args:
            dimension: Embedding vector dimension (default 384).
        """
        self._dim = dimension
        logger.debug(
            f"LocalSemanticEmbeddingProvider initialized (dimension={self._dim})"
        )

    @property
    def dimension(self) -> int:
        """Return vector dimension."""
        return self._dim

    def embed_text(self, text: str) -> list[float]:
        """Generate a 384-dimensional L2-normalized semantic embedding vector.

        Args:
            text: Input text string.

        Returns:
            list[float]: 384-dimensional normalized float list.
        """
        if not text.strip():
            return [0.0] * self._dim

        words = re.findall(r"\w+", text.lower())
        if not words:
            return [0.0] * self._dim

        vec = np.zeros(self._dim, dtype=np.float32)

        # 1. Feature hashing across character n-grams and word tokens
        for word in words:
            # Word token hash projection
            w_hash = hash(word) % self._dim
            vec[w_hash] += 1.0

            # Subword 3-gram hash projection for morphological similarity
            for i in range(len(word) - 2):
                ngram = word[i : i + 3]
                n_hash = (hash(ngram) * 31) % self._dim
                vec[n_hash] += 0.5

        # 2. Add sub-vector position encoding for context variance
        for i, word in enumerate(words[:50]):
            pos_hash = (hash(word) + i) % self._dim
            vec[pos_hash] += 0.25

        # 3. L2 Normalize vector
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm

        return vec.tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a batch of text strings.

        Args:
            texts: List of text strings.

        Returns:
            list[list[float]]: List of 384-dim normalized float lists.
        """
        return [self.embed_text(t) for t in texts]
