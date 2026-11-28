"""Account-scoped YouTube data models for Phase 5 (FR-3, FR-4, DATA-16-21)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


@dataclass(frozen=True)
class LikedVideo:
    """Liked video metadata. Never includes ``liked_at`` (unavailable in API)."""

    video_id: str
    title: str | None
    description: str | None
    tags: tuple[str, ...] | None
    category_id: str | None
    channel_id: str
    channel_title: str | None
    duration_seconds: int | None
    video_published_at: datetime | None
    invalid_fields: tuple[str, ...] = ()


@dataclass(frozen=True)
class Subscription:
    """Account subscription with creation timestamp."""

    subscription_id: str
    channel_id: str
    channel_title: str | None
    subscription_created_at: datetime | None
    invalid_fields: tuple[str, ...] = ()


@dataclass(frozen=True)
class PlaylistSummary:
    """Owned playlist summary (carries no time basis)."""

    playlist_id: str
    title: str | None
    item_count: int | None
    invalid_fields: tuple[str, ...] = ()


@dataclass(frozen=True)
class PlaylistItem:
    """Item inside a playlist with ``playlist_item_added_at`` time basis."""

    playlist_item_id: str
    video_id: str
    position: int | None
    playlist_item_added_at: datetime | None
    invalid_fields: tuple[str, ...] = ()
