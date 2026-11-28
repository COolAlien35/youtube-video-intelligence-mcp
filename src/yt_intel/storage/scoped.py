"""Tenant-scoped SQLAlchemy session wrapper."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeVar, cast

from sqlalchemy import Select, select

from yt_intel.common.errors import AppError, ErrorCode
from yt_intel.common.types import Principal
from yt_intel.storage.db import scoped_select
from yt_intel.storage.models import DailyQuotaRecord

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.orm import Session

_ModelT = TypeVar("_ModelT")
_SHARED_MODELS: frozenset[type[Any]] = frozenset({DailyQuotaRecord})


class ScopedSession:
    """Wrap a SQLAlchemy Session so principal-owned queries and writes are tenant-isolated."""

    def __init__(self, session: Session, principal: Principal) -> None:
        if not isinstance(principal, Principal):
            raise AppError(ErrorCode.FORBIDDEN, "ScopedSession requires a valid Principal")
        self._session = session
        self.principal = principal

    @property
    def raw_session(self) -> Session:
        """Expose underlying Session for controlled shared/admin operations."""
        return self._session

    def select(self, model: type[_ModelT]) -> Select[tuple[_ModelT]]:
        """Build a SELECT statement automatically filtered by ``principal.key``."""
        if hasattr(model, "principal_key"):
            return scoped_select(model, self.principal.key)
        if model in _SHARED_MODELS:
            return select(model)
        raise AppError(
            ErrorCode.FORBIDDEN,
            "Unscoped table access is prohibited without principal_key",
            details={"model": model.__name__},
        )

    def add(self, record: Any) -> None:
        """Stage *record* after enforcing tenant ownership."""
        if hasattr(record, "principal_key"):
            existing = getattr(record, "principal_key", "")
            if not existing:
                record.principal_key = self.principal.key
            elif existing != self.principal.key:
                raise AppError(
                    ErrorCode.FORBIDDEN,
                    "Cross-tenant write is prohibited",
                )
        self._session.add(record)

    def delete(self, record: Any) -> None:
        """Delete *record* after enforcing tenant ownership."""
        if hasattr(record, "principal_key"):
            owner = getattr(record, "principal_key", "")
            if owner != self.principal.key:
                raise AppError(
                    ErrorCode.FORBIDDEN,
                    "Cross-tenant delete is prohibited",
                )
        self._session.delete(record)

    def scalar_one_or_none(self, stmt: Select[tuple[_ModelT]]) -> _ModelT | None:
        """Execute *stmt* and return one scalar result or None."""
        return cast("_ModelT | None", self._session.scalars(stmt).one_or_none())

    def scalars(self, stmt: Select[tuple[_ModelT]]) -> Sequence[_ModelT]:
        """Execute *stmt* and return all scalar results."""
        return cast("Sequence[_ModelT]", self._session.scalars(stmt).all())

    def flush(self) -> None:
        """Flush pending changes to SQLite."""
        self._session.flush()
