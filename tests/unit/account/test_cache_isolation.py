"""Tests for account signal cache isolation, purge hooks, and key uniqueness."""

from __future__ import annotations

from typing import TYPE_CHECKING

from yt_intel.account.loader import _cache_key
from yt_intel.account.types import SignalKind
from yt_intel.cache.store import CacheStore
from yt_intel.common.types import Principal
from yt_intel.config.settings import Settings
from yt_intel.storage import ScopedSession, get_engine, init_db, session_scope

if TYPE_CHECKING:
    from pathlib import Path


def test_account_cache_keys_do_not_collide() -> None:
    k1 = _cache_key(SignalKind.LIKED_VIDEOS, "iss|alice", like_cap=100)
    k2 = _cache_key(SignalKind.LIKED_VIDEOS, "iss|alice", like_cap=200)
    k3 = _cache_key(SignalKind.SUBSCRIPTIONS, "iss|alice", like_cap=0)
    k4 = _cache_key(SignalKind.LIKED_VIDEOS, "iss|bob", like_cap=100)
    k5 = _cache_key(SignalKind.PLAYLIST_ITEMS, "iss|alice", playlist_id="PL1")
    k6 = _cache_key(SignalKind.PLAYLIST_ITEMS, "iss|alice", playlist_id="PL2")
    assert len({k1, k2, k3, k4, k5, k6}) == 6


def test_cache_principal_isolation_and_purge_hooks(tmp_path: Path) -> None:
    alice = Principal(issuer="https://issuer.example", subject="alice")
    bob = Principal(issuer="https://issuer.example", subject="bob")
    settings = Settings(_env_file=None, data_dir=tmp_path / "data")
    engine = get_engine(settings)
    init_db(engine)

    with session_scope(engine) as session:
        alice_cache = CacheStore(ScopedSession(session, alice))
        bob_cache = CacheStore(ScopedSession(session, bob))

        alice_cache.put("account_liked", "k1", {"items": [1]})
        alice_cache.put("account_subscriptions", "k2", {"items": [2]})
        bob_cache.put("account_liked", "k1", {"items": [99]})

        # Cross-principal read isolation
        assert alice_cache.get("account_liked", "k1") is not None
        assert alice_cache.get("account_liked", "k1").value == {"items": [1]}  # type: ignore[union-attr]
        assert bob_cache.get("account_liked", "k1").value == {"items": [99]}  # type: ignore[union-attr]
        assert bob_cache.get("account_subscriptions", "k2") is None

        # purge_kind removes only that kind for alice; others and bob remain
        removed = alice_cache.purge_kind("account_liked")
        assert removed == 1
        assert alice_cache.get("account_liked", "k1") is None
        assert alice_cache.get("account_subscriptions", "k2") is not None
        assert bob_cache.get("account_liked", "k1") is not None

        # purge_principal removes remaining entries for alice; bob remains untouched
        removed_all = alice_cache.purge_principal()
        assert removed_all == 1
        assert alice_cache.get("account_subscriptions", "k2") is None
        assert bob_cache.get("account_liked", "k1") is not None
