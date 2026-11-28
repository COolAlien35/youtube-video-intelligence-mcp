"""Shared account-signal types and coverage labels for Phase 5."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

    from yt_intel.provider.account_models import (
        LikedVideo,
        PlaylistItem,
        PlaylistSummary,
        Subscription,
    )


class SignalKind(StrEnum):
    """Account signal categories exposed by AccountSignalsLoader."""

    LIKED_VIDEOS = "liked_videos"
    SUBSCRIPTIONS = "subscriptions"
    PLAYLISTS = "playlists"
    PLAYLIST_ITEMS = "playlist_items"


@dataclass(frozen=True)
class Coverage:
    """Provenance, time-basis, and truncation metadata for a loaded signal set."""

    source: str
    unit: str
    time_basis: str | None
    fetched_count: int
    reported_total: int | None
    cap: int | None
    truncated: bool
    truncation_reason: str | None
    fetched_at: datetime
    from_cache: bool


@dataclass(frozen=True)
class SignalSet[T_co]:
    """Loaded items for one signal kind paired with its Coverage."""

    items: tuple[T_co, ...]
    coverage: Coverage


@dataclass(frozen=True)
class AccountSignals:
    """Container holding loaded SignalSet instances per requested SignalKind."""

    liked_videos: SignalSet[LikedVideo] | None = None
    subscriptions: SignalSet[Subscription] | None = None
    playlists: SignalSet[PlaylistSummary] | None = None
    playlist_items: dict[str, SignalSet[PlaylistItem]] | None = None
