"""Principal-scoped cache store backed by CacheEntryRecord (24 h default / 30 d ceiling)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from sqlalchemy import or_

from yt_intel.common.clock import Clock, SystemClock
from yt_intel.common.errors import AppError, ErrorCode
from yt_intel.storage.models import CacheEntryRecord

if TYPE_CHECKING:
    from collections.abc import Sequence

    from yt_intel.storage.scoped import ScopedSession

MAX_CACHE_TTL = timedelta(days=30)
DEFAULT_CACHE_TTL = timedelta(hours=24)
DEFAULT_MAX_VALUE_BYTES = 262_144


@dataclass(frozen=True)
class CachedValue:
    """Deserialized cache entry returned by CacheStore."""

    kind: str
    key: str
    value: Any
    fetched_at: datetime
    expires_at: datetime


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


class CacheStore:
    """Principal-scoped cache enforcing TTL and a hard 30-day ceiling from ``fetched_at``."""

    def __init__(
        self,
        scoped_session: ScopedSession,
        *,
        clock: Clock | None = None,
        max_value_bytes: int = DEFAULT_MAX_VALUE_BYTES,
    ) -> None:
        if max_value_bytes <= 0:
            raise ValueError("max_value_bytes must be > 0")
        self._scoped = scoped_session
        self._clock: Clock = clock if clock is not None else SystemClock()
        self._max_value_bytes = max_value_bytes

    def _is_fresh(self, record: CacheEntryRecord, now: datetime) -> bool:
        fetched = _ensure_utc(record.fetched_at)
        expires = _ensure_utc(record.expires_at)
        ceiling = fetched + MAX_CACHE_TTL
        return now < min(expires, ceiling)

    def _to_cached_value(self, record: CacheEntryRecord) -> CachedValue:
        fetched = _ensure_utc(record.fetched_at)
        expires = min(_ensure_utc(record.expires_at), fetched + MAX_CACHE_TTL)
        return CachedValue(
            kind=record.category,
            key=record.canonical_resource_id,
            value=json.loads(record.payload),
            fetched_at=fetched,
            expires_at=expires,
        )

    def get(self, kind: str, key: str) -> CachedValue | None:
        """Return a fresh CachedValue for *(kind, key)* or None if missing/expired."""
        if not kind.strip() or not key.strip():
            return None
        now = self._clock.now().astimezone(UTC)
        stmt = self._scoped.select(CacheEntryRecord).where(
            CacheEntryRecord.category == kind,
            CacheEntryRecord.canonical_resource_id == key,
            CacheEntryRecord.account_ref.is_(None),
        )
        record = self._scoped.scalar_one_or_none(stmt)
        if record is None or not self._is_fresh(record, now):
            return None
        return self._to_cached_value(record)

    def get_many(self, kind: str, keys: Sequence[str]) -> dict[str, CachedValue]:
        """Return a mapping of *key -> CachedValue* for all fresh entries in *keys*."""
        unique_keys = [k for k in dict.fromkeys(keys) if k.strip()]
        if not kind.strip() or not unique_keys:
            return {}
        now = self._clock.now().astimezone(UTC)
        stmt = self._scoped.select(CacheEntryRecord).where(
            CacheEntryRecord.category == kind,
            CacheEntryRecord.canonical_resource_id.in_(unique_keys),
            CacheEntryRecord.account_ref.is_(None),
        )
        records = self._scoped.scalars(stmt)
        return {
            rec.canonical_resource_id: self._to_cached_value(rec)
            for rec in records
            if self._is_fresh(rec, now)
        }

    def put(
        self,
        kind: str,
        key: str,
        value: Any,
        *,
        ttl: timedelta = DEFAULT_CACHE_TTL,
    ) -> CachedValue:
        """Store *value* under *(kind, key)*, clamped to the 30-day ceiling."""
        if not kind.strip() or not key.strip():
            raise AppError(ErrorCode.INVALID_INPUT, "Cache kind and key must not be empty")
        if ttl <= timedelta(0):
            raise AppError(ErrorCode.INVALID_INPUT, "Cache ttl must be positive")

        try:
            payload = json.dumps(value, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise AppError(ErrorCode.INVALID_INPUT, "Cache value must be valid JSON") from exc

        if len(payload.encode("utf-8")) > self._max_value_bytes:
            raise AppError(
                ErrorCode.INVALID_INPUT,
                "Cache value exceeds maximum allowed byte size",
                details={"max_value_bytes": self._max_value_bytes},
            )

        now = self._clock.now().astimezone(UTC)
        effective_ttl = min(ttl, MAX_CACHE_TTL)
        expires_at = now + effective_ttl

        stmt = self._scoped.select(CacheEntryRecord).where(
            CacheEntryRecord.category == kind,
            CacheEntryRecord.canonical_resource_id == key,
            CacheEntryRecord.account_ref.is_(None),
        )
        existing = self._scoped.scalar_one_or_none(stmt)
        if existing is not None:
            existing.fetched_at = now
            existing.expires_at = expires_at
            existing.payload = payload
            self._scoped.flush()
            return self._to_cached_value(existing)

        record = CacheEntryRecord(
            principal_key=self._scoped.principal.key,
            category=kind,
            canonical_resource_id=key,
            account_ref=None,
            fetched_at=now,
            expires_at=expires_at,
            payload=payload,
        )
        self._scoped.add(record)
        self._scoped.flush()
        return self._to_cached_value(record)

    def purge_expired(self) -> int:
        """Delete expired or >30-day-old cache entries for the scoped principal."""
        now = self._clock.now().astimezone(UTC)
        ceiling_cutoff = now - MAX_CACHE_TTL
        stmt = self._scoped.select(CacheEntryRecord).where(
            or_(
                CacheEntryRecord.expires_at <= now,
                CacheEntryRecord.fetched_at <= ceiling_cutoff,
            )
        )
        expired = self._scoped.scalars(stmt)
        for record in expired:
            self._scoped.delete(record)
        self._scoped.flush()
        return len(expired)

    def purge_principal(self) -> int:
        """Delete all cache entries for the scoped principal."""
        stmt = self._scoped.select(CacheEntryRecord)
        records = self._scoped.scalars(stmt)
        for record in records:
            self._scoped.delete(record)
        self._scoped.flush()
        return len(records)

    def purge_kind(self, kind: str) -> int:
        """Delete all cache entries of *kind* for the scoped principal."""
        if not kind.strip():
            return 0
        stmt = self._scoped.select(CacheEntryRecord).where(CacheEntryRecord.category == kind)
        records = self._scoped.scalars(stmt)
        for record in records:
            self._scoped.delete(record)
        self._scoped.flush()
        return len(records)
