"""Account provider protocol and shared YouTube API v3 response parsers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

from yt_intel.common.durations import DurationParseError, parse_iso8601_duration
from yt_intel.common.errors import AppError, ErrorCode
from yt_intel.common.ids import parse_playlist_id, parse_video_id
from yt_intel.common.timeutil import parse_rfc3339_utc
from yt_intel.provider.account_models import (
    LikedVideo,
    PlaylistItem,
    PlaylistSummary,
    Subscription,
)

if TYPE_CHECKING:
    from datetime import datetime

    from yt_intel.common.types import Principal

_CHANNEL_ID_RE = re.compile(r"UC[a-zA-Z0-9_-]{22}")


@dataclass(frozen=True)
class Page[T]:
    """One page of parsed account provider items."""

    items: tuple[T, ...]
    next_page_token: str | None
    reported_total: int | None


class AccountProvider(Protocol):
    """Protocol for account-scoped YouTube Data API v3 read operations."""

    async def list_liked_videos(
        self,
        principal: Principal,
        *,
        page_token: str | None = None,
        page_size: int = 50,
    ) -> Page[LikedVideo]:
        """Return a page of liked videos for *principal*."""
        ...

    async def list_subscriptions(
        self,
        principal: Principal,
        *,
        page_token: str | None = None,
        page_size: int = 50,
    ) -> Page[Subscription]:
        """Return a page of subscriptions for *principal*."""
        ...

    async def list_playlists(
        self,
        principal: Principal,
        *,
        page_token: str | None = None,
        page_size: int = 50,
    ) -> Page[PlaylistSummary]:
        """Return a page of owned playlists for *principal*."""
        ...

    async def list_playlist_items(
        self,
        principal: Principal,
        playlist_id: str,
        *,
        page_token: str | None = None,
        page_size: int = 50,
    ) -> Page[PlaylistItem]:
        """Return a page of items inside *playlist_id* for *principal*."""
        ...


def _upstream_error(message: str) -> AppError:
    return AppError(ErrorCode.UPSTREAM_ERROR, message)


def _require_nonempty_str(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise _upstream_error(f"Missing or invalid required field: {field}")
    return value


def _require_video_id(value: Any, field: str = "video_id") -> str:
    raw = _require_nonempty_str(value, field)
    try:
        return parse_video_id(raw)
    except AppError as exc:
        raise _upstream_error(f"Invalid video ID in upstream payload ({field})") from exc


def _require_channel_id(value: Any, field: str = "channel_id") -> str:
    raw = _require_nonempty_str(value, field)
    if not _CHANNEL_ID_RE.fullmatch(raw):
        raise _upstream_error(f"Invalid channel ID in upstream payload ({field})")
    return raw


def _require_playlist_id(value: Any, field: str = "playlist_id") -> str:
    raw = _require_nonempty_str(value, field)
    try:
        return parse_playlist_id(raw)
    except AppError as exc:
        raise _upstream_error(f"Invalid playlist ID in upstream payload ({field})") from exc


def _opt_str(value: Any, field: str, invalid: list[str]) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    invalid.append(field)
    return None


def _opt_nonneg_int(value: Any, field: str, invalid: list[str]) -> int | None:
    if value is None:
        return None
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return value
    invalid.append(field)
    return None


def _opt_timestamp(value: Any, field: str, invalid: list[str]) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str):
        invalid.append(field)
        return None
    try:
        return parse_rfc3339_utc(value)
    except ValueError:
        invalid.append(field)
        return None


def _opt_duration(value: Any, invalid: list[str]) -> int | None:
    if value is None:
        return None
    if not isinstance(value, str):
        invalid.append("duration_seconds")
        return None
    try:
        return parse_iso8601_duration(value)
    except DurationParseError:
        invalid.append("duration_seconds")
        return None


def _opt_tags(value: Any, invalid: list[str]) -> tuple[str, ...] | None:
    if value is None:
        return None
    if isinstance(value, list) and all(isinstance(tag, str) for tag in value):
        return tuple(value)
    invalid.append("tags")
    return None


def _extract_page_meta(raw: dict[str, Any]) -> tuple[list[dict[str, Any]], str | None, int | None]:
    if not isinstance(raw, dict):
        raise _upstream_error("Upstream response must be a JSON object")
    items = raw.get("items")
    if not isinstance(items, list):
        raise _upstream_error("Upstream response missing 'items' list")
    for item in items:
        if not isinstance(item, dict):
            raise _upstream_error("Upstream item must be a JSON object")
    next_token = raw.get("nextPageToken")
    if next_token is not None and not isinstance(next_token, str):
        next_token = None
    page_info = raw.get("pageInfo")
    reported_total: int | None = None
    if isinstance(page_info, dict):
        total = page_info.get("totalResults")
        if isinstance(total, int) and not isinstance(total, bool) and total >= 0:
            reported_total = total
    return items, next_token, reported_total


def parse_liked_videos_response(raw: dict[str, Any]) -> Page[LikedVideo]:
    """Parse a ``videos.list?myRating=like`` JSON payload into ``Page[LikedVideo]``."""
    raw_items, next_token, reported_total = _extract_page_meta(raw)
    parsed: list[LikedVideo] = []
    for item in raw_items:
        snippet = item.get("snippet")
        if not isinstance(snippet, dict):
            raise _upstream_error("Liked video item missing 'snippet' object")
        content = item.get("contentDetails")
        if content is not None and not isinstance(content, dict):
            content = {}
        invalid: list[str] = []
        video_id = _require_video_id(item.get("id"))
        channel_id = _require_channel_id(snippet.get("channelId"))
        parsed.append(
            LikedVideo(
                video_id=video_id,
                title=_opt_str(snippet.get("title"), "title", invalid),
                description=_opt_str(snippet.get("description"), "description", invalid),
                tags=_opt_tags(snippet.get("tags"), invalid),
                category_id=_opt_str(snippet.get("categoryId"), "category_id", invalid),
                channel_id=channel_id,
                channel_title=_opt_str(snippet.get("channelTitle"), "channel_title", invalid),
                duration_seconds=_opt_duration(
                    content.get("duration") if isinstance(content, dict) else None,
                    invalid,
                ),
                video_published_at=_opt_timestamp(
                    snippet.get("publishedAt"),
                    "video_published_at",
                    invalid,
                ),
                invalid_fields=tuple(invalid),
            )
        )
    return Page(items=tuple(parsed), next_page_token=next_token, reported_total=reported_total)


def parse_subscriptions_response(raw: dict[str, Any]) -> Page[Subscription]:
    """Parse a ``subscriptions.list?mine=true`` JSON payload into ``Page[Subscription]``."""
    raw_items, next_token, reported_total = _extract_page_meta(raw)
    parsed: list[Subscription] = []
    for item in raw_items:
        snippet = item.get("snippet")
        if not isinstance(snippet, dict):
            raise _upstream_error("Subscription item missing 'snippet' object")
        resource = snippet.get("resourceId")
        if not isinstance(resource, dict):
            raise _upstream_error("Subscription snippet missing 'resourceId' object")
        invalid: list[str] = []
        sub_id = _require_nonempty_str(item.get("id"), "subscription_id")
        channel_id = _require_channel_id(resource.get("channelId"))
        parsed.append(
            Subscription(
                subscription_id=sub_id,
                channel_id=channel_id,
                channel_title=_opt_str(snippet.get("title"), "channel_title", invalid),
                subscription_created_at=_opt_timestamp(
                    snippet.get("publishedAt"),
                    "subscription_created_at",
                    invalid,
                ),
                invalid_fields=tuple(invalid),
            )
        )
    return Page(items=tuple(parsed), next_page_token=next_token, reported_total=reported_total)


def parse_playlists_response(raw: dict[str, Any]) -> Page[PlaylistSummary]:
    """Parse a ``playlists.list?mine=true`` JSON payload into ``Page[PlaylistSummary]``."""
    raw_items, next_token, reported_total = _extract_page_meta(raw)
    parsed: list[PlaylistSummary] = []
    for item in raw_items:
        snippet = item.get("snippet")
        if snippet is not None and not isinstance(snippet, dict):
            snippet = {}
        content = item.get("contentDetails")
        if content is not None and not isinstance(content, dict):
            content = {}
        invalid: list[str] = []
        playlist_id = _require_playlist_id(item.get("id"))
        parsed.append(
            PlaylistSummary(
                playlist_id=playlist_id,
                title=_opt_str(
                    snippet.get("title") if isinstance(snippet, dict) else None,
                    "title",
                    invalid,
                ),
                item_count=_opt_nonneg_int(
                    content.get("itemCount") if isinstance(content, dict) else None,
                    "item_count",
                    invalid,
                ),
                invalid_fields=tuple(invalid),
            )
        )
    return Page(items=tuple(parsed), next_page_token=next_token, reported_total=reported_total)


def parse_playlist_items_response(raw: dict[str, Any]) -> Page[PlaylistItem]:
    """Parse a ``playlistItems.list`` JSON payload into ``Page[PlaylistItem]``."""
    raw_items, next_token, reported_total = _extract_page_meta(raw)
    parsed: list[PlaylistItem] = []
    for item in raw_items:
        snippet = item.get("snippet")
        if not isinstance(snippet, dict):
            raise _upstream_error("PlaylistItem missing 'snippet' object")
        resource = snippet.get("resourceId")
        if not isinstance(resource, dict):
            raise _upstream_error("PlaylistItem snippet missing 'resourceId' object")
        invalid: list[str] = []
        item_id = _require_nonempty_str(item.get("id"), "playlist_item_id")
        video_id = _require_video_id(resource.get("videoId"))
        parsed.append(
            PlaylistItem(
                playlist_item_id=item_id,
                video_id=video_id,
                position=_opt_nonneg_int(snippet.get("position"), "position", invalid),
                playlist_item_added_at=_opt_timestamp(
                    snippet.get("publishedAt"),
                    "playlist_item_added_at",
                    invalid,
                ),
                invalid_fields=tuple(invalid),
            )
        )
    return Page(items=tuple(parsed), next_page_token=next_token, reported_total=reported_total)
