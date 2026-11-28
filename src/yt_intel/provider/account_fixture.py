"""Fixture-backed AccountProvider for offline Phase 5 testing."""

from __future__ import annotations

import json
from collections import Counter
from typing import TYPE_CHECKING, Any

from yt_intel.common.errors import AppError, ErrorCode
from yt_intel.provider.account import (
    Page,
    parse_liked_videos_response,
    parse_playlist_items_response,
    parse_playlists_response,
    parse_subscriptions_response,
)
from yt_intel.provider.error_mapping import map_api_error

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from pathlib import Path

    from yt_intel.common.types import Principal
    from yt_intel.provider.account_models import (
        LikedVideo,
        PlaylistItem,
        PlaylistSummary,
        Subscription,
    )
    from yt_intel.provider.fixture import FaultPlan


class FixtureAccountProvider:
    """Offline AccountProvider mapping principal keys to synthetic fixture sets."""

    def __init__(
        self,
        sets: Mapping[str, str],
        fixtures_dir: Path | None = None,
        *,
        raw_sets: Mapping[str, Mapping[str, dict[str, Any]]] | None = None,
        faults: FaultPlan | None = None,
    ) -> None:
        self._sets = dict(sets)
        self._fixtures_dir = fixtures_dir
        self._raw_sets: dict[str, dict[str, dict[str, Any]]] = (
            {k: dict(v) for k, v in raw_sets.items()} if raw_sets is not None else {}
        )
        self.faults = faults
        self.calls: Counter[str] = Counter()

    def _record_call(self, method: str) -> None:
        self.calls[method] += 1
        fault = self.faults
        if fault and fault.method == method and self.calls[method] == fault.nth:
            raise map_api_error(fault.status, fault.reason)

    def _set_name(self, principal: Principal) -> str:
        set_name = self._sets.get(principal.key)
        if set_name is None:
            raise AppError(ErrorCode.AUTH_REQUIRED, "Principal is not connected to a fixture set")
        return set_name

    def _load_raw(self, set_name: str, resource: str) -> dict[str, Any]:
        if set_name in self._raw_sets and resource in self._raw_sets[set_name]:
            return self._raw_sets[set_name][resource]
        if self._fixtures_dir is not None:
            path = self._fixtures_dir / set_name / f"{resource}.json"
            if path.is_file():
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return data
        raise AppError(
            ErrorCode.NOT_FOUND_OR_UNAVAILABLE,
            f"Fixture resource {resource!r} not found for set {set_name!r}",
        )

    def _paginate[T](
        self,
        raw: dict[str, Any],
        parser: Callable[[dict[str, Any]], Page[T]],
        *,
        page_token: str | None,
        page_size: int,
    ) -> Page[T]:
        if not 1 <= page_size <= 50:
            raise AppError(ErrorCode.INVALID_INPUT, "page_size must be between 1 and 50")
        all_items = raw.get("items")
        if not isinstance(all_items, list):
            return parser(raw)

        offset = 0
        if page_token is not None:
            if not page_token.startswith("offset:"):
                raise AppError(ErrorCode.INVALID_INPUT, "Invalid page_token")
            try:
                offset = int(page_token.removeprefix("offset:"))
            except ValueError as exc:
                raise AppError(ErrorCode.INVALID_INPUT, "Invalid page_token") from exc
            if offset < 0 or offset > len(all_items):
                raise AppError(ErrorCode.INVALID_INPUT, "Invalid page_token")

        end = offset + page_size
        next_token = f"offset:{end}" if end < len(all_items) else None
        page_info = raw.get("pageInfo")
        reported_total = (
            page_info.get("totalResults")
            if isinstance(page_info, dict) and "totalResults" in page_info
            else len(all_items)
        )
        sliced_raw: dict[str, Any] = {
            "items": all_items[offset:end],
            "pageInfo": {"totalResults": reported_total},
        }
        if next_token is not None:
            sliced_raw["nextPageToken"] = next_token
        return parser(sliced_raw)

    async def list_liked_videos(
        self,
        principal: Principal,
        *,
        page_token: str | None = None,
        page_size: int = 50,
    ) -> Page[LikedVideo]:
        self._record_call("list_liked_videos")
        raw = self._load_raw(self._set_name(principal), "likes")
        return self._paginate(
            raw, parse_liked_videos_response, page_token=page_token, page_size=page_size
        )

    async def list_subscriptions(
        self,
        principal: Principal,
        *,
        page_token: str | None = None,
        page_size: int = 50,
    ) -> Page[Subscription]:
        self._record_call("list_subscriptions")
        raw = self._load_raw(self._set_name(principal), "subscriptions")
        return self._paginate(
            raw, parse_subscriptions_response, page_token=page_token, page_size=page_size
        )

    async def list_playlists(
        self,
        principal: Principal,
        *,
        page_token: str | None = None,
        page_size: int = 50,
    ) -> Page[PlaylistSummary]:
        self._record_call("list_playlists")
        raw = self._load_raw(self._set_name(principal), "playlists")
        return self._paginate(
            raw, parse_playlists_response, page_token=page_token, page_size=page_size
        )

    async def list_playlist_items(
        self,
        principal: Principal,
        playlist_id: str,
        *,
        page_token: str | None = None,
        page_size: int = 50,
    ) -> Page[PlaylistItem]:
        self._record_call("list_playlist_items")
        raw = self._load_raw(self._set_name(principal), playlist_id)
        return self._paginate(
            raw, parse_playlist_items_response, page_token=page_token, page_size=page_size
        )
