"""SQLite-backed vector storage provider with NumPy vectorized cosine similarity."""

import json
from typing import Any

import numpy as np
from loguru import logger
from sqlalchemy import Index, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from core.vector.base import VectorRecord, VectorSearchHit, VectorStore


class VectorBase(DeclarativeBase):
    """Declarative base for vector store tables."""

    pass


class VectorItemTable(VectorBase):
    """SQLite ORM model storing vector embeddings and metadata."""

    __tablename__ = "vector_store_items"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    meeting_id: Mapped[str] = mapped_column(String(36), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_id: Mapped[str] = mapped_column(String(36), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    vector_json: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")

    __table_args__ = (
        Index("idx_vec_meeting", "meeting_id"),
        Index("idx_vec_entity", "entity_type"),
    )


class SQLiteVectorStore(VectorStore):
    """SQLite vector storage provider with fast NumPy cosine similarity search."""

    def __init__(self, db_url: str = "sqlite:///:memory:") -> None:
        """Initialize SQLiteVectorStore.

        Args:
            db_url: SQLAlchemy database URL string.
        """
        connect_args = {"check_same_thread": False} if "sqlite" in db_url else {}
        engine_kwargs: dict[str, Any] = {"connect_args": connect_args, "echo": False}
        if ":memory:" in db_url:
            from sqlalchemy.pool import StaticPool

            engine_kwargs["poolclass"] = StaticPool

        self._engine = create_engine(db_url, **engine_kwargs)
        VectorBase.metadata.create_all(bind=self._engine)
        self._session_factory = sessionmaker(bind=self._engine, expire_on_commit=False)

        # In-memory numpy matrix cache for high-speed similarity search
        self._records_cache: list[VectorRecord] = []
        self._matrix_cache: np.ndarray | None = None
        self._reload_cache()
        logger.debug(f"SQLiteVectorStore initialized at {db_url}")

    def _reload_cache(self) -> None:
        """Reload in-memory vector cache from SQLite DB."""
        with self._session_factory() as session:
            stmt = select(VectorItemTable)
            items = list(session.scalars(stmt).all())

        records: list[VectorRecord] = []
        vecs: list[list[float]] = []

        for item in items:
            try:
                v = list(json.loads(item.vector_json))
                meta = dict(json.loads(item.metadata_json))
                rec = VectorRecord(
                    id=item.id,
                    vector=v,
                    content=item.content,
                    entity_type=item.entity_type,
                    meeting_id=item.meeting_id,
                    source_id=item.source_id,
                    metadata=meta,
                )
                records.append(rec)
                vecs.append(v)
            except Exception as exc:
                logger.warning(f"Error parsing cached vector record {item.id}: {exc}")

        self._records_cache = records
        if vecs:
            mat = np.array(vecs, dtype=np.float32)
            # Pre-normalize vectors to L2 norm 1.0 for fast dot-product
            norms = np.linalg.norm(mat, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            self._matrix_cache = mat / norms
        else:
            self._matrix_cache = None

    def add_records(self, records: list[VectorRecord]) -> None:
        """Add or update vector records in SQLite store.

        Args:
            records: List of VectorRecord objects to insert.
        """
        if not records:
            return

        with self._session_factory() as session:
            for r in records:
                item = session.get(VectorItemTable, r.id)
                if item:
                    item.meeting_id = r.meeting_id
                    item.entity_type = r.entity_type
                    item.source_id = r.source_id
                    item.content = r.content
                    item.vector_json = json.dumps(r.vector)
                    item.metadata_json = json.dumps(r.metadata)
                else:
                    new_item = VectorItemTable(
                        id=r.id,
                        meeting_id=r.meeting_id,
                        entity_type=r.entity_type,
                        source_id=r.source_id,
                        content=r.content,
                        vector_json=json.dumps(r.vector),
                        metadata_json=json.dumps(r.metadata),
                    )
                    session.add(new_item)
            session.commit()

        self._reload_cache()

    def search(
        self,
        query_vector: list[float],
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[VectorSearchHit]:
        """Perform vectorized cosine similarity search across indexed records.

        Args:
            query_vector: Query embedding float list.
            top_k: Maximum hits to return.
            filters: Optional metadata filters (e.g. meeting_id, entity_type).

        Returns:
            list[VectorSearchHit]: Ranked search hits sorted by score descending.
        """
        if not self._records_cache or self._matrix_cache is None:
            return []

        q_arr = np.array(query_vector, dtype=np.float32)
        q_norm = np.linalg.norm(q_arr)
        if q_norm == 0:
            return []
        q_unit = q_arr / q_norm

        # Compute dot-product cosine similarity
        scores: np.ndarray = np.dot(self._matrix_cache, q_unit)

        hits: list[VectorSearchHit] = []
        filter_meeting = filters.get("meeting_id") if filters else None
        filter_entity = filters.get("entity_type") if filters else None

        for idx, rec in enumerate(self._records_cache):
            if filter_meeting and rec.meeting_id != filter_meeting:
                continue
            if filter_entity and rec.entity_type != filter_entity:
                continue

            score = float(scores[idx])
            hits.append(VectorSearchHit(record=rec, score=score))

        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:top_k]

    def delete_by_meeting(self, meeting_id: str) -> int:
        """Delete all vector records for a target meeting.

        Args:
            meeting_id: Target meeting UUID string.

        Returns:
            int: Number of deleted records.
        """
        with self._session_factory() as session:
            stmt = select(VectorItemTable).where(
                VectorItemTable.meeting_id == meeting_id
            )
            items = list(session.scalars(stmt).all())
            for item in items:
                session.delete(item)
            session.commit()
            count = len(items)

        self._reload_cache()
        return count

    def count(self) -> int:
        """Return total count of vectors in the store.

        Returns:
            int: Total vector count.
        """
        return len(self._records_cache)
