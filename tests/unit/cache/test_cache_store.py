"""Unit tests for principal-scoped CacheStore (TTL, 30-day ceiling, isolation, purge)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest

from yt_intel.cache import MAX_CACHE_TTL, CacheStore
from yt_intel.common import AppError, ErrorCode, FakeClock, Principal
from yt_intel.config import Settings
from yt_intel.storage import ScopedSession, get_engine, init_db, session_scope

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.unit


def test_cache_put_get_many_and_ttl_expiry(tmp_path: Path) -> None:
    """put/get/get_many round-trip JSON values and expire cleanly at TTL."""
    engine = get_engine(Settings(_env_file=None, data_dir=tmp_path / "c1"))
    init_db(engine)
    clock = FakeClock(datetime(2026, 11, 27, 12, 0, tzinfo=UTC))
    alice = Principal(issuer="https://issuer.example", subject="alice")

    with session_scope(engine) as session:
        store = CacheStore(ScopedSession(session, alice), clock=clock)
        store.put("video", "vid-1", {"title": "One"}, ttl=timedelta(hours=1))
        store.put("video", "vid-2", {"title": "Two"}, ttl=timedelta(hours=2))

        found = store.get_many("video", ["vid-1", "vid-2", "vid-missing"])
        assert set(found.keys()) == {"vid-1", "vid-2"}
        assert found["vid-1"].value == {"title": "One"}

        clock.advance(3600)
        assert store.get("video", "vid-1") is None
        assert store.get("video", "vid-2") is not None
        assert store.purge_expired() == 1


def test_cache_enforces_30_day_ceiling_and_principal_isolation(tmp_path: Path) -> None:
    """Entries never outlive 30 days from fetched_at and are isolated per principal."""
    engine = get_engine(Settings(_env_file=None, data_dir=tmp_path / "c2"))
    init_db(engine)
    clock = FakeClock(datetime(2026, 11, 1, 0, 0, tzinfo=UTC))
    alice = Principal(issuer="https://issuer.example", subject="alice")
    bob = Principal(issuer="https://issuer.example", subject="bob")

    with session_scope(engine) as session:
        store_a = CacheStore(ScopedSession(session, alice), clock=clock)
        entry = store_a.put("channel", "ch-1", {"name": "Alice"}, ttl=timedelta(days=90))
        assert entry.expires_at == entry.fetched_at + MAX_CACHE_TTL

        store_b = CacheStore(ScopedSession(session, bob), clock=clock)
        assert store_b.get("channel", "ch-1") is None

        clock.advance(30 * 86400)
        assert store_a.get("channel", "ch-1") is None


def test_cache_rejects_oversize_values(tmp_path: Path) -> None:
    """Values exceeding max_value_bytes are rejected with INVALID_INPUT."""
    engine = get_engine(Settings(_env_file=None, data_dir=tmp_path / "c3"))
    init_db(engine)
    alice = Principal(issuer="https://issuer.example", subject="alice")

    with session_scope(engine) as session:
        store = CacheStore(ScopedSession(session, alice), max_value_bytes=64)
        with pytest.raises(AppError) as exc_info:
            store.put("video", "vid-big", {"blob": "x" * 200})
        assert exc_info.value.code is ErrorCode.INVALID_INPUT
