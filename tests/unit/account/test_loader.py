"""Unit tests for AccountSignalsLoader."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from yt_intel.account.loader import AccountSignalsLoader
from yt_intel.account.types import SignalKind
from yt_intel.cache.store import CacheStore
from yt_intel.common.errors import AppError, ErrorCode
from yt_intel.common.types import Principal
from yt_intel.config.settings import Settings
from yt_intel.provider.account_fixture import FixtureAccountProvider
from yt_intel.quota.limits import PrincipalLimiter
from yt_intel.quota.preflight import QuotaPlanner
from yt_intel.quota.service import QuotaService
from yt_intel.storage import ScopedSession, get_engine, init_db, session_scope

if TYPE_CHECKING:
    from pathlib import Path

_CHAN = "UC1234567890123456789012"
_READONLY_SCOPE = "https://www.googleapis.com/auth/youtube.readonly"


def _make_like(vid: str) -> dict[str, Any]:
    return {
        "id": vid,
        "snippet": {
            "channelId": _CHAN,
            "title": f"Video {vid}",
            "publishedAt": "2026-11-01T00:00:00Z",
        },
        "contentDetails": {"duration": "PT3M"},
    }


def _make_sub(sub_id: str, chan_id: str) -> dict[str, Any]:
    return {
        "id": sub_id,
        "snippet": {
            "title": f"Channel {chan_id}",
            "publishedAt": "2026-10-01T00:00:00Z",
            "resourceId": {"channelId": chan_id},
        },
    }


def _make_engine_and_service(tmp_path: Path) -> tuple[Any, QuotaService]:
    settings = Settings(_env_file=None, data_dir=tmp_path / "data")
    engine = get_engine(settings)
    init_db(engine)
    service = QuotaService(engine, settings)
    return engine, service


def _make_loader(
    tmp_path: Path,
    principal: Principal,
    provider: FixtureAccountProvider,
    *,
    like_cap: int = 1000,
    sub_cap: int = 500,
    playlist_cap: int = 200,
    playlist_items_cap: int = 500,
    max_playlists_per_run: int = 5,
    cache_ttl_hours: int = 24,
    quota_common_cap: int = 2000,
) -> tuple[AccountSignalsLoader, Any, CacheStore]:
    settings = Settings(
        _env_file=None,
        data_dir=tmp_path / "data",
        account_like_cap=like_cap,
        account_subscription_cap=sub_cap,
        account_playlist_cap=playlist_cap,
        account_playlist_items_cap=playlist_items_cap,
        max_playlists_per_run=max_playlists_per_run,
        account_cache_ttl_hours=cache_ttl_hours,
        quota_common_daily_cap=quota_common_cap,
    )
    engine = get_engine(settings)
    init_db(engine)
    service = QuotaService(engine, settings)
    planner = QuotaPlanner(service)
    limiter = PrincipalLimiter(engine, settings)

    with session_scope(engine) as session:
        scoped = ScopedSession(session, principal)
        cache = CacheStore(scoped)
        loader = AccountSignalsLoader(provider, cache, planner, limiter, settings)
        return loader, engine, cache


async def test_loader_cache_hit_makes_zero_provider_calls(tmp_path: Path) -> None:
    principal = Principal(issuer="https://issuer.example", subject="alice")
    raw_sets = {
        "set_a": {
            "likes": {"items": [_make_like(f"vid{i:08d}") for i in range(5)]},
        }
    }
    provider = FixtureAccountProvider({principal.key: "set_a"}, raw_sets=raw_sets)

    settings = Settings(
        _env_file=None,
        data_dir=tmp_path / "data",
        account_like_cap=10,
        account_subscription_cap=500,
        account_playlist_cap=200,
        account_playlist_items_cap=500,
        max_playlists_per_run=5,
        account_cache_ttl_hours=24,
        quota_common_daily_cap=2000,
    )
    engine = get_engine(settings)
    init_db(engine)
    service = QuotaService(engine, settings)
    planner = QuotaPlanner(service)
    limiter = PrincipalLimiter(engine, settings)

    with session_scope(engine) as session:
        scoped = ScopedSession(session, principal)
        cache = CacheStore(scoped)
        loader = AccountSignalsLoader(provider, cache, planner, limiter, settings)

        # First call fetches from provider
        result1 = await loader.load(principal, frozenset({SignalKind.LIKED_VIDEOS}))
        assert result1.liked_videos is not None
        assert provider.calls["list_liked_videos"] == 1
        session.commit()

        # Second call should be a cache hit → zero extra provider calls
        result2 = await loader.load(principal, frozenset({SignalKind.LIKED_VIDEOS}))
        assert result2.liked_videos is not None
        assert result2.liked_videos.coverage.from_cache is True
        assert len(result2.liked_videos.items) == 5
        assert provider.calls["list_liked_videos"] == 1  # still 1


async def test_loader_over_budget_rejection_with_zero_provider_calls(tmp_path: Path) -> None:
    principal = Principal(issuer="https://issuer.example", subject="alice")
    raw_sets = {
        "set_a": {
            "likes": {"items": [_make_like(f"vid{i:08d}") for i in range(5)]},
        }
    }
    provider = FixtureAccountProvider({principal.key: "set_a"}, raw_sets=raw_sets)

    # Quota cap of 1 unit total — will reject the preflight reservation
    settings = Settings(
        _env_file=None,
        data_dir=tmp_path / "data",
        account_like_cap=1000,  # would need many pages
        account_subscription_cap=500,
        account_playlist_cap=200,
        account_playlist_items_cap=500,
        max_playlists_per_run=5,
        account_cache_ttl_hours=24,
        quota_common_daily_cap=1,  # only 1 unit total
    )
    engine = get_engine(settings)
    init_db(engine)
    service = QuotaService(engine, settings)
    planner = QuotaPlanner(service)
    limiter = PrincipalLimiter(engine, settings)

    with session_scope(engine) as session:
        scoped = ScopedSession(session, principal)
        cache = CacheStore(scoped)
        loader = AccountSignalsLoader(provider, cache, planner, limiter, settings)

        with pytest.raises(AppError) as exc:
            await loader.load(principal, frozenset({SignalKind.LIKED_VIDEOS}))
        assert exc.value.code is ErrorCode.QUOTA_EXCEEDED
        assert provider.calls["list_liked_videos"] == 0  # zero provider calls


async def test_loader_too_many_playlist_ids_rejected(tmp_path: Path) -> None:
    principal = Principal(issuer="https://issuer.example", subject="alice")
    provider = FixtureAccountProvider({principal.key: "set_a"}, raw_sets={"set_a": {}})
    settings = Settings(
        _env_file=None,
        data_dir=tmp_path / "data",
        max_playlists_per_run=2,
        account_like_cap=1000,
        account_subscription_cap=500,
        account_playlist_cap=200,
        account_playlist_items_cap=500,
        account_cache_ttl_hours=24,
    )
    engine = get_engine(settings)
    init_db(engine)
    service = QuotaService(engine, settings)
    planner = QuotaPlanner(service)
    limiter = PrincipalLimiter(engine, settings)

    with session_scope(engine) as session:
        scoped = ScopedSession(session, principal)
        cache = CacheStore(scoped)
        loader = AccountSignalsLoader(provider, cache, planner, limiter, settings)

        with pytest.raises(AppError) as exc:
            await loader.load(
                principal,
                frozenset({SignalKind.PLAYLIST_ITEMS}),
                playlist_ids=["PL1", "PL2", "PL3"],  # exceeds max=2
            )
        assert exc.value.code is ErrorCode.INVALID_INPUT


async def test_loader_refresh_true_re_fetches(tmp_path: Path) -> None:
    principal = Principal(issuer="https://issuer.example", subject="alice")
    raw_sets = {
        "set_a": {
            "likes": {"items": [_make_like(f"vid{i:08d}") for i in range(3)]},
        }
    }
    provider = FixtureAccountProvider({principal.key: "set_a"}, raw_sets=raw_sets)
    settings = Settings(
        _env_file=None,
        data_dir=tmp_path / "data",
        account_like_cap=10,
        account_subscription_cap=500,
        account_playlist_cap=200,
        account_playlist_items_cap=500,
        max_playlists_per_run=5,
        account_cache_ttl_hours=24,
        quota_common_daily_cap=200,
    )
    engine = get_engine(settings)
    init_db(engine)
    service = QuotaService(engine, settings)
    planner = QuotaPlanner(service)
    limiter = PrincipalLimiter(engine, settings)

    with session_scope(engine) as session:
        scoped = ScopedSession(session, principal)
        cache = CacheStore(scoped)
        loader = AccountSignalsLoader(provider, cache, planner, limiter, settings)

        await loader.load(principal, frozenset({SignalKind.LIKED_VIDEOS}))
        assert provider.calls["list_liked_videos"] == 1
        session.commit()

        # refresh=True must bypass cache and re-fetch
        result = await loader.load(principal, frozenset({SignalKind.LIKED_VIDEOS}), refresh=True)
        assert provider.calls["list_liked_videos"] == 2
        assert result.liked_videos is not None
        assert result.liked_videos.coverage.from_cache is False
