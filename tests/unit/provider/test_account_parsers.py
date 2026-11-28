"""Unit tests for Phase 5 account response parsers."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from yt_intel.common.errors import AppError, ErrorCode
from yt_intel.provider.account import (
    parse_liked_videos_response,
    parse_playlist_items_response,
    parse_playlists_response,
    parse_subscriptions_response,
)

_CHANNEL_ID = "UC1234567890123456789012"


def test_parse_liked_videos_valid_and_missing_fields_stay_none() -> None:
    raw = {
        "pageInfo": {"totalResults": 2},
        "nextPageToken": "page-2",
        "items": [
            {
                "id": "dQw4w9WgXcQ",
                "snippet": {
                    "channelId": _CHANNEL_ID,
                    "title": "Video A",
                    "description": "Desc",
                    "tags": ["a", "b"],
                    "categoryId": "27",
                    "channelTitle": "Chan",
                    "publishedAt": "2026-11-20T12:00:00Z",
                },
                "contentDetails": {"duration": "PT3M33S"},
            },
            {
                "id": "abcdefghijk",
                "snippet": {
                    "channelId": _CHANNEL_ID,
                },
            },
        ],
    }
    page = parse_liked_videos_response(raw)
    assert page.reported_total == 2
    assert page.next_page_token == "page-2"  # noqa: S105
    first, second = page.items
    assert first.video_id == "dQw4w9WgXcQ"
    assert first.duration_seconds == 213
    assert first.video_published_at == datetime(2026, 11, 20, 12, 0, tzinfo=UTC)
    assert first.invalid_fields == ()
    assert not hasattr(first, "liked_at")

    assert second.title is None
    assert second.description is None
    assert second.duration_seconds is None
    assert second.video_published_at is None
    assert second.invalid_fields == ()


def test_parse_liked_videos_invalid_duration_and_timestamp_become_none() -> None:
    raw = {
        "items": [
            {
                "id": "dQw4w9WgXcQ",
                "snippet": {
                    "channelId": _CHANNEL_ID,
                    "publishedAt": "not-a-timestamp",
                    "tags": "not-a-list",
                },
                "contentDetails": {"duration": "BAD_DUR"},
            }
        ]
    }
    page = parse_liked_videos_response(raw)
    item = page.items[0]
    assert item.duration_seconds is None
    assert item.video_published_at is None
    assert item.tags is None
    assert set(item.invalid_fields) == {"duration_seconds", "video_published_at", "tags"}


def test_parse_rejects_bad_ids() -> None:
    bad_video = {
        "items": [
            {
                "id": "bad",
                "snippet": {"channelId": _CHANNEL_ID},
            }
        ]
    }
    with pytest.raises(AppError) as exc:
        parse_liked_videos_response(bad_video)
    assert exc.value.code is ErrorCode.UPSTREAM_ERROR

    bad_sub = {
        "items": [
            {
                "id": "sub-1",
                "snippet": {"resourceId": {"channelId": "not-a-uc-id"}},
            }
        ]
    }
    with pytest.raises(AppError) as exc2:
        parse_subscriptions_response(bad_sub)
    assert exc2.value.code is ErrorCode.UPSTREAM_ERROR


def test_parse_subscriptions_playlists_and_items() -> None:
    subs = parse_subscriptions_response(
        {
            "items": [
                {
                    "id": "sub-1",
                    "snippet": {
                        "title": "Sub Chan",
                        "publishedAt": "2026-10-01T00:00:00Z",
                        "resourceId": {"channelId": _CHANNEL_ID},
                    },
                }
            ]
        }
    )
    assert subs.items[0].subscription_id == "sub-1"
    assert subs.items[0].subscription_created_at == datetime(2026, 10, 1, tzinfo=UTC)

    playlists = parse_playlists_response(
        {
            "items": [
                {
                    "id": "PL12345",
                    "snippet": {"title": "Study"},
                    "contentDetails": {"itemCount": -5},
                }
            ]
        }
    )
    assert playlists.items[0].item_count is None
    assert playlists.items[0].invalid_fields == ("item_count",)

    items = parse_playlist_items_response(
        {
            "items": [
                {
                    "id": "pli-1",
                    "snippet": {
                        "position": 0,
                        "publishedAt": "2026-11-01T05:00:00Z",
                        "resourceId": {"videoId": "dQw4w9WgXcQ"},
                    },
                }
            ]
        }
    )
    assert items.items[0].position == 0
    assert items.items[0].playlist_item_added_at == datetime(2026, 11, 1, 5, 0, tzinfo=UTC)
