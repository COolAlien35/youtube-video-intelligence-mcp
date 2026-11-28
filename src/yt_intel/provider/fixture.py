"""Offline provider. FaultPlan raises once, before the numbered method call mutates state."""

import json
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from yt_intel.common.errors import AppError, ErrorCode
from yt_intel.common.ids import ChannelRef
from yt_intel.common.timeutil import parse_rfc3339_utc

from . import normalize
from .error_mapping import map_api_error
from .models import (
    AccountRef,
    Channel,
    ChannelBatch,
    ChannelSearchPage,
    PlaylistItem,
    PlaylistSummary,
    SearchPage,
    Subscription,
    VideoBatch,
    VideoMetadata,
)


@dataclass(frozen=True)
class FaultPlan:
    method: str
    nth: int = 1
    status: int = 500
    reason: str = "backendError"


class FixtureProvider:
    def __init__(self, fixtures_dir: Path, faults: FaultPlan | None = None) -> None:
        self.raw: dict[str, dict[str, Any]] = {
            path.relative_to(fixtures_dir).with_suffix("").as_posix(): json.loads(
                path.read_text(encoding="utf8")
            )
            for path in sorted(fixtures_dir.rglob("*.json"))
        }
        self.videos = {
            item["id"]: normalize.video(item)
            for name, page in self.raw.items()
            if name.startswith("videos.list-")
            for item in page["items"]
        }
        self.channels = {
            item["id"]: normalize.channel(item)
            for page in (self.raw["channels.list"], self.raw.get("fr2/channels.synthetic", {}))
            for item in page.get("items", [])
        }
        for vid, video in self.videos.items():
            channel = self.channels.get(video.channel_id)
            if video.channel_title is None and channel is not None:
                self.videos[vid] = replace(video, channel_title=channel.title)
        self.video_search_topics = sorted(
            (
                key.removeprefix("search.list/").removesuffix("-1")
                for key in self.raw
                if key.startswith("search.list/") and key.endswith("-1")
            ),
            key=lambda topic: (-len(topic), topic),
        )
        self.faults = faults
        self.calls: Counter[str] = Counter()
        self.playlists: dict[str, dict[str, PlaylistSummary]] = {}
        self.items: dict[tuple[str, str], list[PlaylistItem]] = {}
        for key, page in self.raw.items():
            if key.endswith("/playlists"):
                owner = key.split("/")[0]
                self.playlists[owner] = {}
                for entry in page["items"]:
                    pid = entry["id"]
                    snippet = entry["snippet"]
                    self.playlists[owner][pid] = PlaylistSummary(
                        pid,
                        snippet["title"],
                        snippet["description"],
                        entry["status"]["privacyStatus"],
                    )
                    self.items[owner, pid] = [
                        PlaylistItem(
                            item["id"],
                            pid,
                            item["snippet"]["resourceId"]["videoId"],
                            item["snippet"]["position"],
                            parse_rfc3339_utc(item["snippet"]["publishedAt"]),
                        )
                        for item in self.raw[f"{owner}/{pid}"]["items"]
                    ]

    def _call(self, method: str) -> None:
        self.calls[method] += 1
        fault = self.faults
        if fault and fault.method == method and self.calls[method] == fault.nth:
            raise map_api_error(fault.status, fault.reason)

    def _owner(self, account: AccountRef) -> str:
        key = account.principal_key
        if key not in self.playlists and key != "user_nochannel":
            raise AppError(ErrorCode.AUTH_REQUIRED, "Unknown fixture account")
        return key

    async def get_videos(self, video_ids: Sequence[str]) -> VideoBatch:
        self._call("get_videos")
        return VideoBatch(
            tuple(self.videos[i] for i in video_ids if i in self.videos),
            tuple(i for i in video_ids if i not in self.videos),
        )

    async def get_channels(self, channel_ids: Sequence[str]) -> ChannelBatch:
        self._call("get_channels")
        return ChannelBatch(
            tuple(self.channels[i] for i in channel_ids if i in self.channels),
            tuple(i for i in channel_ids if i not in self.channels),
        )

    async def resolve_channel(self, ref: ChannelRef) -> Channel | None:
        self._call("resolve_channel")
        if ref.kind == "id":
            return self.channels.get(ref.value)
        return next(
            (
                c
                for c in self.channels.values()
                if (
                    (c.handle or "").casefold() == ref.value.casefold()
                    if ref.kind == "handle"
                    else c.username == ref.value
                )
            ),
            None,
        )

    async def search_channels(
        self, query: str, *, max_results: int = 50, page_token: str | None = None
    ) -> ChannelSearchPage:
        self._call("search_channels")
        if not 1 <= max_results <= 50:
            raise map_api_error(400, "invalidParameter")
        ids = self.raw.get("fr2/search.synthetic", {}).get(query.casefold(), [])
        tokens = {f"FAKE_channel_{i}": i for i in range(1, len(ids))}
        if page_token is not None and page_token not in tokens:
            raise map_api_error(400, "invalidParameter")
        start = tokens[page_token] if page_token else 0
        end = start + max_results
        return ChannelSearchPage(
            tuple(ids[start:end]), f"FAKE_channel_{end}" if end < len(ids) else None
        )

    async def search_videos(
        self, query: str, *, max_results: int = 50, page_token: str | None = None
    ) -> SearchPage:
        self._call("search_videos")
        if not 0 <= max_results <= 50:
            raise map_api_error(400, "invalidParameter")
        normalized = query.strip().casefold()
        topic = next(
            (
                topic
                for topic in self.video_search_topics
                if normalized == topic or normalized.startswith(topic + " ")
            ),
            normalized,
        )
        first = self.raw.get(f"search.list/{topic}-1", {})
        second = self.raw.get(f"search.list/{topic}-2", {}) if first.get("nextPageToken") else {}
        ids = [item["id"]["videoId"] for page in (first, second) for item in page.get("items", [])]
        tokens = {f"FAKE_{topic}_{i}": i for i in range(1, len(ids))}
        offset = 0
        if page_token is not None:
            if page_token not in tokens:
                raise map_api_error(400, "invalidParameter")
            offset = tokens[page_token]
        end = offset + max_results
        return SearchPage(
            tuple(ids[offset:end]),
            f"FAKE_{topic}_{end}" if max_results and end < len(ids) else None,
        )

    async def list_liked_videos(
        self, account: AccountRef, *, limit: int = 1000
    ) -> list[VideoMetadata]:
        self._call("list_liked_videos")
        owner = self._owner(account)
        if limit < 0:
            raise map_api_error(400, "invalidParameter")
        return [
            normalize.video(item)
            for item in self.raw.get(f"{owner}/likes", {}).get("items", [])[: min(limit, 1000)]
        ]

    async def list_subscriptions(self, account: AccountRef) -> list[Subscription]:
        self._call("list_subscriptions")
        owner = self._owner(account)
        return [
            Subscription(
                item["snippet"]["resourceId"]["channelId"],
                parse_rfc3339_utc(item["snippet"]["publishedAt"]),
            )
            for item in self.raw.get(f"{owner}/subscriptions", {}).get("items", [])
        ]

    async def get_own_channel(self, account: AccountRef) -> Channel:
        self._call("get_own_channel")
        raw = self.raw[f"{self._owner(account)}/channel"]
        if "error" in raw:
            error = raw["error"]
            raise map_api_error(error["code"], error["errors"][0]["reason"])
        return normalize.channel(raw["items"][0])

    async def list_playlists(self, account: AccountRef) -> list[PlaylistSummary]:
        self._call("list_playlists")
        return list(self.playlists.get(self._owner(account), {}).values())

    def _playlist_items(self, account: AccountRef, pid: str) -> list[PlaylistItem]:
        key = (self._owner(account), pid)
        if key not in self.items:
            raise map_api_error(404, "playlistNotFound")
        return self.items[key]

    async def list_playlist_items(
        self, account: AccountRef, playlist_id: str
    ) -> list[PlaylistItem]:
        self._call("list_playlist_items")
        return self._playlist_items(account, playlist_id).copy()

    async def create_playlist(
        self, account: AccountRef, title: str, description: str, visibility: str
    ) -> str:
        self._call("create_playlist")
        await self.get_own_channel(account)
        if visibility not in {"private", "public", "unlisted"}:
            raise map_api_error(400, "invalidParameter")
        owner = account.principal_key
        pid = f"PLSYN_{owner}_{len(self.playlists[owner])}"
        self.playlists[owner][pid] = PlaylistSummary(pid, title, description, visibility)
        self.items[owner, pid] = []
        return pid

    async def insert_playlist_item(
        self, account: AccountRef, playlist_id: str, video_id: str
    ) -> str:
        self._call("insert_playlist_item")
        items = self._playlist_items(account, playlist_id)
        if video_id not in self.videos:
            raise map_api_error(404, "videoNotFound")
        position = len(items)
        item_id = f"SYNITEM_{playlist_id}_{position}"
        items.append(PlaylistItem(item_id, playlist_id, video_id, position, None))
        return item_id
