"""Database Engine providing SQLite/SQLAlchemy session management and initialization."""

from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from loguru import logger
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy declarative ORM models."""

    pass


class DatabaseEngine:
    """Manages database connection pool, engine configuration, and sessions."""

    def __init__(
        self, db_url: str = "sqlite:///~/.gemini/antigravity-ide/echomind.db"
    ) -> None:
        """Initialize DatabaseEngine instance.

        Args:
            db_url: Database connection string. Defaults to local SQLite file.
        """
        import os

        if db_url.startswith("sqlite:///~/"):
            expanded_path = os.path.expanduser(db_url.replace("sqlite:///", ""))
            os.makedirs(os.path.dirname(expanded_path), exist_ok=True)
            db_url = f"sqlite:///{expanded_path}"

        self._db_url = db_url
        is_sqlite = db_url.startswith("sqlite")

        connect_args = {}
        engine_kwargs: dict[str, Any] = {"echo": False, "future": True}

        if is_sqlite:
            connect_args["check_same_thread"] = False
            if ":memory:" in db_url:
                engine_kwargs["poolclass"] = StaticPool

        self._engine = create_engine(
            db_url,
            connect_args=connect_args,
            **engine_kwargs,
        )

        # Enable foreign key constraints and WAL mode for SQLite
        if is_sqlite and ":memory:" not in self._db_url:

            @event.listens_for(self._engine, "connect")
            def set_sqlite_pragma(
                dbapi_connection: Any, connection_record: Any
            ) -> None:
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.close()

        self._session_factory = sessionmaker(
            bind=self._engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
            class_=Session,
        )

        logger.debug(f"DatabaseEngine initialized with URL: {self._db_url}")

    @property
    def db_url(self) -> str:
        """Access database connection URL."""
        return self._db_url

    def init_db(self) -> None:
        """Initialize schema and migrate missing columns."""
        try:
            import modules.meeting_intelligence.models  # noqa: F401
            import modules.search.models  # noqa: F401
            import modules.speaker.models  # noqa: F401
            import modules.storage.models  # noqa: F401
            import modules.summary.models  # noqa: F401

            Base.metadata.create_all(bind=self._engine)

            # Self-healing migration for SQLite columns added across development phases
            with self._engine.connect() as conn:
                inspector = inspect(self._engine)
                if "speakers" in inspector.get_table_names():
                    cols = [c["name"] for c in inspector.get_columns("speakers")]
                    if "display_name" not in cols:
                        conn.execute(
                            text("ALTER TABLE speakers ADD COLUMN display_name TEXT")
                        )
                        logger.info(
                            "Migrated column 'display_name' into table 'speakers'."
                        )
                    if "color" not in cols:
                        conn.execute(
                            text("ALTER TABLE speakers ADD COLUMN color VARCHAR(32)")
                        )
                    if "created_at" not in cols:
                        conn.execute(
                            text("ALTER TABLE speakers ADD COLUMN created_at DATETIME")
                        )
                    if "last_seen" not in cols:
                        conn.execute(
                            text("ALTER TABLE speakers ADD COLUMN last_seen DATETIME")
                        )

                if "transcripts" in inspector.get_table_names():
                    t_cols = [c["name"] for c in inspector.get_columns("transcripts")]
                    if "translated_text" not in t_cols:
                        conn.execute(
                            text(
                                "ALTER TABLE transcripts "
                                "ADD COLUMN translated_text TEXT"
                            )
                        )
                    if "speaker_label" not in t_cols:
                        conn.execute(
                            text(
                                "ALTER TABLE transcripts ADD COLUMN speaker_label TEXT"
                            )
                        )
                    if "embedding_id" not in t_cols:
                        conn.execute(
                            text("ALTER TABLE transcripts ADD COLUMN embedding_id TEXT")
                        )

                conn.commit()

            logger.info("Database schema initialized successfully.")
        except Exception as exc:
            logger.error(f"Failed to initialize database schema: {exc}")
            raise

    def close(self) -> None:
        """Dispose database engine connection pool."""
        self._engine.dispose()

    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """Provide transactional scope around a series of operations."""
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception as exc:
            session.rollback()
            logger.error(f"Database session error, rolling back transaction: {exc}")
            raise
        finally:
            session.close()
