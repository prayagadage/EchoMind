"""Database engine and session management using SQLAlchemy 2.0 ORM."""

from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from loguru import logger
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""

    pass


class DatabaseEngine:
    """Manages SQLite database connections, sessions, and schema migrations."""

    def __init__(self, db_url: str | None = None) -> None:
        """Initialize DatabaseEngine instance.

        Args:
            db_url: SQLAlchemy database URL (defaults to sqlite:///data/db/echomind.db).
        """
        if db_url is None:
            db_path = Path("data/db/echomind.db")
            db_path.parent.mkdir(parents=True, exist_ok=True)
            db_url = f"sqlite:///{db_path.absolute()}"

        self._db_url = db_url
        is_sqlite = self._db_url.startswith("sqlite")

        # Enable multithreaded access for SQLite
        connect_args = {"check_same_thread": False} if is_sqlite else {}
        engine_kwargs: dict[str, Any] = {
            "connect_args": connect_args,
            "echo": False,
            "future": True,
        }

        if ":memory:" in self._db_url:
            from sqlalchemy.pool import StaticPool

            engine_kwargs["poolclass"] = StaticPool

        self._engine = create_engine(self._db_url, **engine_kwargs)

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
        """Initialize database schema by creating all defined ORM tables."""
        try:
            Base.metadata.create_all(bind=self._engine)
            logger.info("Database schema initialized successfully.")
        except Exception as exc:
            logger.error(f"Failed to initialize database schema: {exc}")
            raise

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

    def close(self) -> None:
        """Dispose database engine connections."""
        self._engine.dispose()
        logger.debug("DatabaseEngine connections disposed.")
