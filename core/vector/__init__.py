"""Vector storage abstraction package for EchoMind.

Exposes VectorStore protocol, VectorRecord, VectorSearchHit, and SQLiteVectorStore.
"""

from core.vector.base import VectorRecord, VectorSearchHit, VectorStore
from core.vector.sqlite_provider import SQLiteVectorStore

__all__ = [
    "SQLiteVectorStore",
    "VectorRecord",
    "VectorSearchHit",
    "VectorStore",
]
