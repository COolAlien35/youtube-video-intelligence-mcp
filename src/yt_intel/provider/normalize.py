from typing import Any

from yt_intel.common.durations import duration_seconds_or_none
from yt_intel.common.timeutil import parse_rfc3339_utc

from .models import Channel, VideoMetadata


def video(raw: dict[str, Any]) -> VideoMetadata:
    snippet = raw["snippet"]
    tags = snippet.get("tags")
    count = raw.get("statistics", {}).get("viewCount")
    return VideoMetadata(
        raw["id"],
        snippet["channelId"],
        snippet["title"],
        snippet["description"],
        parse_rfc3339_utc(snippet["publishedAt"]),
        duration_seconds_or_none(raw.get("contentDetails", {}).get("duration")),
        None if tags is None else tuple(tags),
        snippet.get("defaultAudioLanguage"),
        snippet.get("categoryId"),
        None if count is None else int(count),
    )


def channel(raw: dict[str, Any]) -> Channel:
    snippet = raw["snippet"]
    return Channel(raw["id"], snippet["title"], snippet["description"], snippet.get("customUrl"))
