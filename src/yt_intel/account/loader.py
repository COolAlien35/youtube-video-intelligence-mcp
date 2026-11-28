"""AccountSignalsLoader: cache, quota preflight, pagination, and coverage labels."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from yt_intel.account.types import AccountSignals, Coverage, SignalKind, SignalSet
from yt_intel.common.errors import AppError, ErrorCode
from yt_intel.common.request_context import get_request_id
from yt_intel.common.timeutil import parse_rfc3339_utc
from yt_intel.provider.account_models import (
    LikedVideo,
    PlaylistItem,
    PlaylistSummary,
    Subscription,
)
from yt_intel.quota.service import WorkflowCost

if TYPE_CHECKING:
    from collections.abc import Sequence

    from yt_intel.cache.store import CacheStore
    from yt_intel.common.types import Principal
    from yt_intel.config import Settings
    from yt_intel.provider.account import AccountProvider
    from yt_intel.quota.limits import PrincipalLimiter
    from yt_intel.quota.preflight import QuotaPlanner, Reservation

logger = logging.getLogger(__name__)

# Cache kind constants (account data never overlaps with metadata cache kinds)
_KIND_LIKED = "account_liked"
_KIND_SUBS = "account_subscriptions"
_KIND_PLAYLISTS = "account_playlists"
_KIND_PLAYLIST_ITEMS = "account_playlist_items"

_KIND_MAP: dict[SignalKind, str] = {
    SignalKind.LIKED_VIDEOS: _KIND_LIKED,
    SignalKind.SUBSCRIPTIONS: _KIND_SUBS,
    SignalKind.PLAYLISTS: _KIND_PLAYLISTS,
    SignalKind.PLAYLIST_ITEMS: _KIND_PLAYLIST_ITEMS,
}

# YouTube Data API v3 cost per paginated account call (1 unit per call)
_UNITS_PER_PAGE = 1


def _cache_key(kind: SignalKind, principal_key: str, **params: Any) -> str:
    """SHA-256 of (kind, principal_key, sorted params) - 64-char hex key."""
    raw = json.dumps(
        {"kind": str(kind), "pk": principal_key, **params},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _now_utc() -> datetime:
    return datetime.now(UTC)


class AccountSignalsLoader:
    """Loads principal-scoped account signals with cache, quota preflight, and coverage."""

    def __init__(
        self,
        provider: AccountProvider,
        cache: CacheStore,
        planner: QuotaPlanner,
        limiter: PrincipalLimiter,
        settings: Settings,
    ) -> None:
        self._provider = provider
        self._cache = cache
        self._planner = planner
        self._limiter = limiter
        self._settings = settings

    async def load(
        self,
        principal: Principal,
        want: frozenset[SignalKind],
        *,
        playlist_ids: Sequence[str] = (),
        like_cap: int | None = None,
        refresh: bool = False,
    ) -> AccountSignals:
        """Load requested account signals for *principal*."""
        if not want:
            return AccountSignals()

        effective_like_cap = like_cap if like_cap is not None else self._settings.account_like_cap

        # Reject too many playlist IDs upfront (never silently drop)
        if (
            SignalKind.PLAYLIST_ITEMS in want
            and len(playlist_ids) > self._settings.max_playlists_per_run
        ):
            raise AppError(
                ErrorCode.INVALID_INPUT,
                f"Too many playlist IDs: got {len(playlist_ids)}, "
                f"max is {self._settings.max_playlists_per_run}",
                details={"max_playlists_per_run": self._settings.max_playlists_per_run},
            )

        pending_cache_writes: list[tuple[SignalKind, str, SignalSet[Any], timedelta]] = []
        with self._limiter.acquire_workflow(principal):
            signals = await self._load_inside_slot(
                principal,
                want,
                playlist_ids=playlist_ids,
                like_cap=effective_like_cap,
                refresh=refresh,
                pending_cache_writes=pending_cache_writes,
            )

        for kind, key, signal_set, ttl in pending_cache_writes:
            self._put_cache(kind, key, signal_set, ttl=ttl)

        return signals

    async def _load_inside_slot(
        self,
        principal: Principal,
        want: frozenset[SignalKind],
        *,
        playlist_ids: Sequence[str],
        like_cap: int,
        refresh: bool,
        pending_cache_writes: list[tuple[SignalKind, str, SignalSet[Any], timedelta]],
    ) -> AccountSignals:
        ttl = timedelta(hours=self._settings.account_cache_ttl_hours)

        # --- Per-kind cache check (fix: only reserve quota for misses) ---
        cache_hits: dict[SignalKind, Any] = {}
        cache_miss_kinds: set[SignalKind] = set()
        playlist_items_cache_hits: dict[str, Any] = {}
        playlist_items_miss_ids: list[str] = []

        if not refresh:
            for kind in want:
                if kind == SignalKind.PLAYLIST_ITEMS:
                    for pid in playlist_ids:
                        key = _cache_key(kind, principal.key, playlist_id=pid)
                        cv = self._cache.get(_KIND_MAP[kind], key)
                        if cv is not None:
                            playlist_items_cache_hits[pid] = cv.value
                        else:
                            playlist_items_miss_ids.append(pid)
                else:
                    cap_param = like_cap if kind == SignalKind.LIKED_VIDEOS else 0
                    key = _cache_key(kind, principal.key, like_cap=cap_param)
                    cv = self._cache.get(_KIND_MAP[kind], key)
                    if cv is not None:
                        cache_hits[kind] = cv.value
                    else:
                        cache_miss_kinds.add(kind)
        else:
            cache_miss_kinds = set(want) - {SignalKind.PLAYLIST_ITEMS}
            playlist_items_miss_ids = list(playlist_ids)

        # Estimate pages needed for quota planning (conservative: ceil(cap / page_size))
        page_size = 50
        miss_common_units = 0
        for kind in cache_miss_kinds:
            if kind == SignalKind.LIKED_VIDEOS:
                miss_common_units += (like_cap + page_size - 1) // page_size
            elif kind == SignalKind.SUBSCRIPTIONS:
                sub_cap = self._settings.account_subscription_cap
                miss_common_units += (sub_cap + page_size - 1) // page_size
            elif kind == SignalKind.PLAYLISTS:
                pl_cap = self._settings.account_playlist_cap
                miss_common_units += (pl_cap + page_size - 1) // page_size
        if playlist_items_miss_ids:
            items_cap = self._settings.account_playlist_items_cap
            pages_per_pl = (items_cap + page_size - 1) // page_size
            miss_common_units += len(playlist_items_miss_ids) * pages_per_pl

        # --- Reserve quota only for cache misses ---
        reservation: Reservation | None = None
        if miss_common_units > 0:
            plan = WorkflowCost(common_units=miss_common_units)
            reservation = self._planner.reserve(principal, plan)

        try:
            result = await self._fetch_misses(
                principal,
                cache_miss_kinds=cache_miss_kinds,
                playlist_items_miss_ids=playlist_items_miss_ids,
                like_cap=like_cap,
                page_size=page_size,
                ttl=ttl,
                pending_cache_writes=pending_cache_writes,
            )
        except Exception:
            if reservation is not None:
                reservation.release()
            raise

        # Settle actual units
        if reservation is not None:
            actual_units = result.get("actual_units", 0)
            reservation.commit(WorkflowCost(common_units=actual_units))

        # --- Build AccountSignals from cache hits + fresh fetches ---
        liked_set: SignalSet[LikedVideo] | None = None
        subs_set: SignalSet[Subscription] | None = None
        playlists_set: SignalSet[PlaylistSummary] | None = None
        playlist_items_map: dict[str, SignalSet[PlaylistItem]] | None = None

        if SignalKind.LIKED_VIDEOS in want:
            if SignalKind.LIKED_VIDEOS in cache_hits:
                data = cache_hits[SignalKind.LIKED_VIDEOS]
                liked_set = self._liked_set_from_cache(data)
            elif SignalKind.LIKED_VIDEOS in result:
                liked_set = result[SignalKind.LIKED_VIDEOS]

        if SignalKind.SUBSCRIPTIONS in want:
            if SignalKind.SUBSCRIPTIONS in cache_hits:
                data = cache_hits[SignalKind.SUBSCRIPTIONS]
                subs_set = self._subs_set_from_cache(data)
            elif SignalKind.SUBSCRIPTIONS in result:
                subs_set = result[SignalKind.SUBSCRIPTIONS]

        if SignalKind.PLAYLISTS in want:
            if SignalKind.PLAYLISTS in cache_hits:
                data = cache_hits[SignalKind.PLAYLISTS]
                playlists_set = self._playlists_set_from_cache(data)
            elif SignalKind.PLAYLISTS in result:
                playlists_set = result[SignalKind.PLAYLISTS]

        if SignalKind.PLAYLIST_ITEMS in want:
            playlist_items_map = {}
            for pid, data in playlist_items_cache_hits.items():
                playlist_items_map[pid] = self._playlist_items_set_from_cache(data)
            for pid in playlist_items_miss_ids:
                result_key = (SignalKind.PLAYLIST_ITEMS, pid)
                if result_key in result:
                    playlist_items_map[pid] = result[result_key]

        return AccountSignals(
            liked_videos=liked_set,
            subscriptions=subs_set,
            playlists=playlists_set,
            playlist_items=playlist_items_map if SignalKind.PLAYLIST_ITEMS in want else None,
        )

    async def _fetch_misses(
        self,
        principal: Principal,
        *,
        cache_miss_kinds: set[SignalKind],
        playlist_items_miss_ids: list[str],
        like_cap: int,
        page_size: int,
        ttl: timedelta,
        pending_cache_writes: list[tuple[SignalKind, str, SignalSet[Any], timedelta]],
    ) -> dict[Any, Any]:
        result: dict[Any, Any] = {"actual_units": 0}

        if SignalKind.LIKED_VIDEOS in cache_miss_kinds:
            liked_set, units, cache_entry = await self._fetch_liked_videos(
                principal, like_cap=like_cap, page_size=page_size, ttl=ttl
            )
            result[SignalKind.LIKED_VIDEOS] = liked_set
            result["actual_units"] += units
            if cache_entry is not None:
                pending_cache_writes.append(cache_entry)

        if SignalKind.SUBSCRIPTIONS in cache_miss_kinds:
            subs_set, units, cache_entry = await self._fetch_subscriptions(
                principal,
                cap=self._settings.account_subscription_cap,
                page_size=page_size,
                ttl=ttl,
            )
            result[SignalKind.SUBSCRIPTIONS] = subs_set
            result["actual_units"] += units
            if cache_entry is not None:
                pending_cache_writes.append(cache_entry)

        if SignalKind.PLAYLISTS in cache_miss_kinds:
            playlists_set, units, cache_entry = await self._fetch_playlists(
                principal,
                cap=self._settings.account_playlist_cap,
                page_size=page_size,
                ttl=ttl,
            )
            result[SignalKind.PLAYLISTS] = playlists_set
            result["actual_units"] += units
            if cache_entry is not None:
                pending_cache_writes.append(cache_entry)

        for pid in playlist_items_miss_ids:
            items_set, units, cache_entry = await self._fetch_playlist_items(
                principal,
                pid,
                cap=self._settings.account_playlist_items_cap,
                page_size=page_size,
                ttl=ttl,
            )
            result[SignalKind.PLAYLIST_ITEMS, pid] = items_set
            result["actual_units"] += units
            if cache_entry is not None:
                pending_cache_writes.append(cache_entry)

        return result

    async def _fetch_liked_videos(
        self, principal: Principal, *, like_cap: int, page_size: int, ttl: timedelta
    ) -> tuple[
        SignalSet[LikedVideo], int, tuple[SignalKind, str, SignalSet[Any], timedelta] | None
    ]:
        items: list[LikedVideo] = []
        page_token: str | None = None
        pages_fetched = 0
        reported_total: int | None = None
        truncated = False
        truncation_reason: str | None = None
        fetch_error: Exception | None = None

        try:
            while len(items) < like_cap:
                remaining = like_cap - len(items)
                page = await self._provider.list_liked_videos(
                    principal, page_token=page_token, page_size=min(page_size, remaining)
                )
                pages_fetched += 1
                if reported_total is None:
                    reported_total = page.reported_total
                items.extend(page.items)
                if len(items) >= like_cap:
                    truncated = True
                    truncation_reason = "like_cap_reached"
                    break
                if page.next_page_token is None:
                    break
                page_token = page.next_page_token
        except Exception as exc:
            fetch_error = exc
            if pages_fetched == 0:
                raise
            truncated = True
            truncation_reason = "fetch_interrupted"

        fetched_at = _now_utc()
        coverage = Coverage(
            source="provider" if fetch_error is None else "partial_provider",
            unit="liked_videos",
            time_basis="video_published_at",
            fetched_count=len(items),
            reported_total=reported_total,
            cap=like_cap,
            truncated=truncated,
            truncation_reason=truncation_reason,
            fetched_at=fetched_at,
            from_cache=False,
        )

        signal_set: SignalSet[LikedVideo] = SignalSet(items=tuple(items), coverage=coverage)

        # Only cache complete, non-interrupted results
        cache_entry: tuple[SignalKind, str, SignalSet[Any], timedelta] | None = None
        if fetch_error is None:
            cache_entry = (
                SignalKind.LIKED_VIDEOS,
                _cache_key(SignalKind.LIKED_VIDEOS, principal.key, like_cap=like_cap),
                signal_set,
                ttl,
            )
            logger.info(
                "account_liked_videos_fetched",
                extra={"request_id": get_request_id(), "count": len(items), "pages": pages_fetched},
            )

        return signal_set, pages_fetched, cache_entry

    async def _fetch_subscriptions(
        self, principal: Principal, *, cap: int, page_size: int, ttl: timedelta
    ) -> tuple[
        SignalSet[Subscription], int, tuple[SignalKind, str, SignalSet[Any], timedelta] | None
    ]:
        items: list[Subscription] = []
        page_token: str | None = None
        pages_fetched = 0
        reported_total: int | None = None
        truncated = False
        truncation_reason: str | None = None
        fetch_error: Exception | None = None

        try:
            while len(items) < cap:
                page = await self._provider.list_subscriptions(
                    principal, page_token=page_token, page_size=min(page_size, cap - len(items))
                )
                pages_fetched += 1
                if reported_total is None:
                    reported_total = page.reported_total
                items.extend(page.items)
                if len(items) >= cap:
                    truncated = True
                    truncation_reason = "subscription_cap_reached"
                    break
                if page.next_page_token is None:
                    break
                page_token = page.next_page_token
        except Exception as exc:
            fetch_error = exc
            if pages_fetched == 0:
                raise
            truncated = True
            truncation_reason = "fetch_interrupted"

        fetched_at = _now_utc()
        coverage = Coverage(
            source="provider" if fetch_error is None else "partial_provider",
            unit="subscriptions",
            time_basis="subscription_created_at",
            fetched_count=len(items),
            reported_total=reported_total,
            cap=cap,
            truncated=truncated,
            truncation_reason=truncation_reason,
            fetched_at=fetched_at,
            from_cache=False,
        )

        signal_set: SignalSet[Subscription] = SignalSet(items=tuple(items), coverage=coverage)
        cache_entry: tuple[SignalKind, str, SignalSet[Any], timedelta] | None = None
        if fetch_error is None:
            cache_entry = (
                SignalKind.SUBSCRIPTIONS,
                _cache_key(SignalKind.SUBSCRIPTIONS, principal.key, like_cap=0),
                signal_set,
                ttl,
            )
            logger.info(
                "account_subscriptions_fetched",
                extra={"request_id": get_request_id(), "count": len(items), "pages": pages_fetched},
            )
        return signal_set, pages_fetched, cache_entry

    async def _fetch_playlists(
        self, principal: Principal, *, cap: int, page_size: int, ttl: timedelta
    ) -> tuple[
        SignalSet[PlaylistSummary], int, tuple[SignalKind, str, SignalSet[Any], timedelta] | None
    ]:
        items: list[PlaylistSummary] = []
        page_token: str | None = None
        pages_fetched = 0
        reported_total: int | None = None
        truncated = False
        truncation_reason: str | None = None
        fetch_error: Exception | None = None

        try:
            while len(items) < cap:
                page = await self._provider.list_playlists(
                    principal, page_token=page_token, page_size=min(page_size, cap - len(items))
                )
                pages_fetched += 1
                if reported_total is None:
                    reported_total = page.reported_total
                items.extend(page.items)
                if len(items) >= cap:
                    truncated = True
                    truncation_reason = "playlist_cap_reached"
                    break
                if page.next_page_token is None:
                    break
                page_token = page.next_page_token
        except Exception as exc:
            fetch_error = exc
            if pages_fetched == 0:
                raise
            truncated = True
            truncation_reason = "fetch_interrupted"

        fetched_at = _now_utc()
        coverage = Coverage(
            source="provider" if fetch_error is None else "partial_provider",
            unit="playlists",
            time_basis=None,
            fetched_count=len(items),
            reported_total=reported_total,
            cap=cap,
            truncated=truncated,
            truncation_reason=truncation_reason,
            fetched_at=fetched_at,
            from_cache=False,
        )
        signal_set: SignalSet[PlaylistSummary] = SignalSet(items=tuple(items), coverage=coverage)
        cache_entry: tuple[SignalKind, str, SignalSet[Any], timedelta] | None = None
        if fetch_error is None:
            cache_entry = (
                SignalKind.PLAYLISTS,
                _cache_key(SignalKind.PLAYLISTS, principal.key, like_cap=0),
                signal_set,
                ttl,
            )
            logger.info(
                "account_playlists_fetched",
                extra={"request_id": get_request_id(), "count": len(items), "pages": pages_fetched},
            )
        return signal_set, pages_fetched, cache_entry

    async def _fetch_playlist_items(
        self, principal: Principal, playlist_id: str, *, cap: int, page_size: int, ttl: timedelta
    ) -> tuple[
        SignalSet[PlaylistItem], int, tuple[SignalKind, str, SignalSet[Any], timedelta] | None
    ]:
        items: list[PlaylistItem] = []
        page_token: str | None = None
        pages_fetched = 0
        reported_total: int | None = None
        truncated = False
        truncation_reason: str | None = None
        fetch_error: Exception | None = None

        try:
            while len(items) < cap:
                page = await self._provider.list_playlist_items(
                    principal,
                    playlist_id,
                    page_token=page_token,
                    page_size=min(page_size, cap - len(items)),
                )
                pages_fetched += 1
                if reported_total is None:
                    reported_total = page.reported_total
                items.extend(page.items)
                if len(items) >= cap:
                    truncated = True
                    truncation_reason = "playlist_items_cap_reached"
                    break
                if page.next_page_token is None:
                    break
                page_token = page.next_page_token
        except Exception as exc:
            fetch_error = exc
            if pages_fetched == 0:
                raise
            truncated = True
            truncation_reason = "fetch_interrupted"

        fetched_at = _now_utc()
        coverage = Coverage(
            source="provider" if fetch_error is None else "partial_provider",
            unit="playlist_items",
            time_basis="playlist_item_added_at",
            fetched_count=len(items),
            reported_total=reported_total,
            cap=cap,
            truncated=truncated,
            truncation_reason=truncation_reason,
            fetched_at=fetched_at,
            from_cache=False,
        )
        signal_set: SignalSet[PlaylistItem] = SignalSet(items=tuple(items), coverage=coverage)
        cache_entry: tuple[SignalKind, str, SignalSet[Any], timedelta] | None = None
        if fetch_error is None:
            cache_entry = (
                SignalKind.PLAYLIST_ITEMS,
                _cache_key(SignalKind.PLAYLIST_ITEMS, principal.key, playlist_id=playlist_id),
                signal_set,
                ttl,
            )
            logger.info(
                "account_playlist_items_fetched",
                extra={
                    "request_id": get_request_id(),
                    "count": len(items),
                    "pages": pages_fetched,
                },
            )
        return signal_set, pages_fetched, cache_entry

    def _put_cache(
        self, kind: SignalKind, key: str, signal_set: SignalSet[Any], *, ttl: timedelta
    ) -> None:
        payload = {
            "items": [
                {k: _json_safe(v) for k, v in vars(item).items() if not k.startswith("_")}
                if hasattr(item, "__dataclass_fields__")
                else str(item)
                for item in signal_set.items
            ],
            "coverage": {k: _json_safe(v) for k, v in vars(signal_set.coverage).items()},
        }
        try:
            self._cache.put(_KIND_MAP[kind], key, payload, ttl=ttl)
        except AppError:
            logger.warning(
                "account_signal_cache_put_failed",
                extra={"kind": str(kind), "request_id": get_request_id()},
            )

    def _liked_set_from_cache(self, data: Any) -> SignalSet[LikedVideo]:
        coverage = self._coverage_from_cache(data, "liked_videos", "video_published_at")
        raw_items = data.get("items", []) if isinstance(data, dict) else []
        items = tuple(
            LikedVideo(
                video_id=str(item["video_id"]),
                title=item.get("title"),
                description=item.get("description"),
                tags=tuple(item["tags"]) if item.get("tags") is not None else None,
                category_id=item.get("category_id"),
                channel_id=str(item["channel_id"]),
                channel_title=item.get("channel_title"),
                duration_seconds=item.get("duration_seconds"),
                video_published_at=_parse_dt(item.get("video_published_at")),
                invalid_fields=tuple(item.get("invalid_fields", ())),
            )
            for item in raw_items
            if isinstance(item, dict)
        )
        return SignalSet(items=items, coverage=coverage)

    def _subs_set_from_cache(self, data: Any) -> SignalSet[Subscription]:
        coverage = self._coverage_from_cache(data, "subscriptions", "subscription_created_at")
        raw_items = data.get("items", []) if isinstance(data, dict) else []
        items = tuple(
            Subscription(
                subscription_id=str(item["subscription_id"]),
                channel_id=str(item["channel_id"]),
                channel_title=item.get("channel_title"),
                subscription_created_at=_parse_dt(item.get("subscription_created_at")),
                invalid_fields=tuple(item.get("invalid_fields", ())),
            )
            for item in raw_items
            if isinstance(item, dict)
        )
        return SignalSet(items=items, coverage=coverage)

    def _playlists_set_from_cache(self, data: Any) -> SignalSet[PlaylistSummary]:
        coverage = self._coverage_from_cache(data, "playlists", None)
        raw_items = data.get("items", []) if isinstance(data, dict) else []
        items = tuple(
            PlaylistSummary(
                playlist_id=str(item["playlist_id"]),
                title=item.get("title"),
                item_count=item.get("item_count"),
                invalid_fields=tuple(item.get("invalid_fields", ())),
            )
            for item in raw_items
            if isinstance(item, dict)
        )
        return SignalSet(items=items, coverage=coverage)

    def _playlist_items_set_from_cache(self, data: Any) -> SignalSet[PlaylistItem]:
        coverage = self._coverage_from_cache(data, "playlist_items", "playlist_item_added_at")
        raw_items = data.get("items", []) if isinstance(data, dict) else []
        items = tuple(
            PlaylistItem(
                playlist_item_id=str(item["playlist_item_id"]),
                video_id=str(item["video_id"]),
                position=item.get("position"),
                playlist_item_added_at=_parse_dt(item.get("playlist_item_added_at")),
                invalid_fields=tuple(item.get("invalid_fields", ())),
            )
            for item in raw_items
            if isinstance(item, dict)
        )
        return SignalSet(items=items, coverage=coverage)

    def _coverage_from_cache(self, data: Any, unit: str, time_basis: str | None) -> Coverage:
        cov_data = data.get("coverage", {}) if isinstance(data, dict) else {}
        fetched_at = _now_utc()
        if isinstance(cov_data, dict):
            parsed = _parse_dt(cov_data.get("fetched_at"))
            if parsed is not None:
                fetched_at = parsed
        return Coverage(
            source="cache",
            unit=unit,
            time_basis=time_basis,
            fetched_count=cov_data.get("fetched_count", 0) if isinstance(cov_data, dict) else 0,
            reported_total=cov_data.get("reported_total") if isinstance(cov_data, dict) else None,
            cap=cov_data.get("cap") if isinstance(cov_data, dict) else None,
            truncated=cov_data.get("truncated", False) if isinstance(cov_data, dict) else False,
            truncation_reason=(
                cov_data.get("truncation_reason") if isinstance(cov_data, dict) else None
            ),
            fetched_at=fetched_at,
            from_cache=True,
        )


def _json_safe(value: Any) -> Any:
    """Convert dataclasses' datetime/tuple fields into JSON-serializable primitives."""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, tuple):
        return [_json_safe(v) for v in value]
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    return value


def _parse_dt(raw: Any) -> datetime | None:
    if not isinstance(raw, str):
        return None
    try:
        return parse_rfc3339_utc(raw)
    except Exception:
        logger.debug("account_cache_timestamp_parse_failed")
        return None
