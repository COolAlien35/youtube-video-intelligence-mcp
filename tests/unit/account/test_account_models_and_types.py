"""Unit tests for Phase 5 account models, loader types, and settings."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from yt_intel.account import AccountSignals, AccountSignalsLoader, Coverage, SignalKind, SignalSet
from yt_intel.common.types import Principal
from yt_intel.config.settings import Settings, validate_settings
from yt_intel.provider.account_models import (
    LikedVideo,
    PlaylistItem,
    PlaylistSummary,
    Subscription,
)


def test_account_models_have_no_liked_at_and_are_frozen() -> None:
    now = datetime(2026, 11, 23, tzinfo=UTC)
    liked = LikedVideo(
        video_id="dQw4w9WgXcQ",
        title="Sample",
        description=None,
        tags=None,
        category_id="27",
        channel_id="UC1234567890123456789012",
        channel_title="Channel",
        duration_seconds=None,
        video_published_at=now,
        invalid_fields=("duration_seconds",),
    )
    assert not hasattr(liked, "liked_at")
    assert liked.invalid_fields == ("duration_seconds",)

    sub = Subscription(
        subscription_id="sub-1",
        channel_id="UC1234567890123456789012",
        channel_title="Channel",
        subscription_created_at=now,
    )
    pl = PlaylistSummary(playlist_id="PL123", title="My List", item_count=10)
    item = PlaylistItem(
        playlist_item_id="item-1",
        video_id="dQw4w9WgXcQ",
        position=0,
        playlist_item_added_at=now,
    )
    cov = Coverage(
        source="fixture",
        unit="videos",
        time_basis="video_published_at",
        fetched_count=1,
        reported_total=1,
        cap=1000,
        truncated=False,
        truncation_reason=None,
        fetched_at=now,
        from_cache=False,
    )
    signals = AccountSignals(
        liked_videos=SignalSet(items=(liked,), coverage=cov),
        subscriptions=SignalSet(items=(sub,), coverage=cov),
        playlists=SignalSet(items=(pl,), coverage=cov),
        playlist_items={"PL123": SignalSet(items=(item,), coverage=cov)},
    )
    assert signals.liked_videos is not None
    assert len(signals.liked_videos.items) == 1


async def test_loader_stub_raises_not_implemented() -> None:
    loader = AccountSignalsLoader()
    principal = Principal(issuer="https://issuer.example", subject="sub-1")
    with pytest.raises(NotImplementedError):
        await loader.load(principal, frozenset({SignalKind.LIKED_VIDEOS}))


def test_account_settings_defaults_and_validation() -> None:
    settings = Settings(_env_file=None)
    validate_settings(settings)
    assert settings.account_cache_ttl_hours == 24
    assert settings.account_like_cap == 1000
    assert settings.account_subscription_cap == 500
    assert settings.account_playlist_cap == 200
    assert settings.account_playlist_items_cap == 500
    assert settings.max_playlists_per_run == 5

    bad = Settings(_env_file=None, max_playlists_per_run=0)
    with pytest.raises(ValueError, match="max_playlists_per_run"):
        validate_settings(bad)
