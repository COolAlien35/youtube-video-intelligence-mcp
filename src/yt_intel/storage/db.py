"""SQLAlchemy engine, session management, UTC type, and principal-scoped query helpers."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Select, TypeDecorator, create_engine, event, select
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

if TYPE_CHECKING:
    from collections.abc import Iterator

    from sqlalchemy.engine import Dialect, Engine

    from yt_intel.config import Settings


class Base(DeclarativeBase):
    """Declarative base for all SQLAlchemy ORM models."""


class UTCDateTime(TypeDecorator[datetime]):
    """Store datetimes in UTC and always return timezone-aware UTC datetimes."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(
        self,
        value: datetime | None,
        dialect: Dialect,
    ) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    def process_result_value(
        self,
        value: datetime | None,
        dialect: Dialect,
    ) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


def _configure_sqlite_pragmas(dbapi_connection: Any, _connection_record: Any) -> None:
    """Enable WAL mode, foreign keys, busy timeout, and NORMAL sync on SQLite connections."""
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.execute("PRAGMA synchronous=NORMAL")
    finally:
        cursor.close()


def get_engine(settings: Settings) -> Engine:
    """Create a SQLAlchemy Engine configured for SQLite WAL, creating data_dir if missing."""
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    is_sqlite = settings.database_url.startswith("sqlite")
    connect_args: dict[str, Any] = {"check_same_thread": False} if is_sqlite else {}
    engine = create_engine(settings.database_url, connect_args=connect_args, future=True)
    if is_sqlite:
        event.listen(engine, "connect", _configure_sqlite_pragmas)
    return engine


@contextmanager
def session_scope(engine: Engine) -> Iterator[Session]:
    """Provide a transactional scope around a series of operations."""
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db(engine: Engine) -> None:
    """Create all tables defined on Base.metadata."""
    Base.metadata.create_all(engine)


def scoped_select(model: type[Any], principal_key: str) -> Select[Any]:
    """Return a SELECT statement filtered by *principal_key*, rejecting empty/blank keys."""
    if not principal_key or not principal_key.strip():
        raise ValueError("principal_key must be a non-empty string")
    if not hasattr(model, "principal_key"):
        raise ValueError(f"{model.__name__} does not have a principal_key column")
    return select(model).where(model.principal_key == principal_key)
