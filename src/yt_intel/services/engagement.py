"""FR-4 orchestration. Account authorization and coverage belong to the signal loader."""

from asyncio import Lock
from collections.abc import Sequence
from contextlib import nullcontext
from dataclasses import replace
from datetime import datetime
from typing import Literal, Protocol

from fastapi.concurrency import contextmanager_in_threadpool
from pydantic import BaseModel, Field, PrivateAttr, model_validator
from sqlalchemy.engine import Engine

from yt_intel.analytics.engine import Metrics, Observation, Source, Window, analyze
from yt_intel.cache.store import CacheStore
from yt_intel.common import Principal
from yt_intel.provider.base import YouTubeProvider
from yt_intel.quota import (
    PrincipalLimiter,
    QuotaPlan,
    QuotaPlanner,
    Reservation,
    batched_lookup_units,
)
from yt_intel.storage import session_scope
from yt_intel.storage.scoped import ScopedSession

LABELS = {
    "liked_videos": ("videos", "video_published_at"),
    "subscriptions": ("subscriptions", "subscription_created_at"),
    "playlist_items": ("playlist items", "playlist_item_added_at"),
}
DETAIL_KIND = "engagement_video_details"
DETAIL_CAP = 100


class EngagementRequest(BaseModel):
    source: Source
    period: Window
    compare_to: Window | None = None
    playlist_id: str | None = None

    @model_validator(mode="after")
    def check_source(self) -> "EngagementRequest":
        if (self.source == "playlist_items") != bool(self.playlist_id and self.playlist_id.strip()):
            raise ValueError("Supply a playlist ID only for playlist items")
        if self.compare_to is None:
            try:
                self.period.start - (self.period.end - self.period.start)
            except OverflowError:
                raise ValueError("Default comparison is outside the supported date range") from None
        return self


class Coverage(BaseModel):
    source: Source
    unit: str
    time_basis: str
    fetched_count: int = Field(ge=0)
    reported_total: int | None = Field(ge=0)
    cap: int | None = Field(ge=0)
    truncated: bool
    truncation_reason: str | None
    fetched_at: datetime
    from_cache: bool


class LoadedSignals(BaseModel):
    _detail_reservation: Reservation | None = PrivateAttr(default=None)
    items: list[Observation]
    coverage: Coverage


class AccountSignalsLoader(Protocol):
    async def load(
        self,
        principal: Principal,
        want: frozenset[Source],
        *,
        playlist_ids: Sequence[str] = (),
        like_cap: int = 1000,
    ) -> dict[Source, LoadedSignals]: ...


class EnrichmentCoverage(BaseModel):
    distinct_video_ids: int
    selected: int
    available: int
    cap: int = DETAIL_CAP
    truncated: bool


class EngagementResult(BaseModel):
    source: Source
    unit: str
    time_basis: str
    timezone: Literal["UTC"] = "UTC"
    period: Window
    coverage: Coverage
    enrichment: EnrichmentCoverage | None
    metrics: Metrics
    qualifiers: list[str]
    insufficient_data: bool
    insufficient_reason: str | None
    provenance: str = (
        "Descriptive statistics for the authorized account sample. "
        "These counts do not measure watch time or quality."
    )


class EngagementService:
    def __init__(
        self,
        loader: AccountSignalsLoader,
        provider: YouTubeProvider,
        engine: Engine,
        planner: QuotaPlanner,
        limiter: PrincipalLimiter,
        consent_lock: Lock | None = None,
    ) -> None:
        self.consent_lock = consent_lock
        self.loader = loader
        self.provider = provider
        self.engine = engine
        self.planner = planner
        self.limiter = limiter

    async def enrich(
        self, principal: Principal, rows: list[Observation], reservation: Reservation | None = None
    ) -> tuple[list[Observation], EnrichmentCoverage]:
        ids = list(dict.fromkeys(r.video_id for r in rows if r.video_id))
        selected = ids[:DETAIL_CAP]
        calls = 0
        try:
            with session_scope(self.engine) as session:
                cache = CacheStore(ScopedSession(session, principal))
                cached = cache.get_many(DETAIL_KIND, selected)
            details = {key: value.value for key, value in cached.items()}
            missing = [key for key in selected if key not in cached]
            if missing:
                reservation = reservation or self.planner.reserve(
                    principal, QuotaPlan(batched_lookup_units(len(missing)))
                )
                for start in range(0, len(missing), 50):
                    batch = missing[start : start + 50]
                    calls += 1
                    videos = await self.provider.get_videos(batch)
                    for video in videos.videos:
                        if video.id in batch and video.id not in videos.unavailable_ids:
                            details[video.id] = {
                                "channel_id": video.channel_id,
                                "category_id": video.category_id,
                                "duration_seconds": video.duration_seconds,
                            }
        finally:
            if reservation:
                reservation.commit(QuotaPlan(calls))
        if missing:
            with session_scope(self.engine) as session:
                cache = CacheStore(ScopedSession(session, principal))
                for key in missing:
                    if key in details:
                        cache.put(DETAIL_KIND, key, details[key])
        enriched = [
            replace(row, **details[row.video_id]) if row.video_id in details else row
            for row in rows
        ]
        return enriched, EnrichmentCoverage(
            distinct_video_ids=len(ids),
            selected=len(selected),
            available=len(details),
            truncated=len(ids) > DETAIL_CAP,
        )

    async def run(self, principal: Principal, request: EngagementRequest) -> EngagementResult:
        async with (
            contextmanager_in_threadpool(self.limiter.acquire_workflow(principal)),
            self.consent_lock or nullcontext(),
        ):
            source = request.source
            sets = await self.loader.load(
                principal,
                frozenset({source}),
                playlist_ids=(request.playlist_id,) if request.playlist_id else (),
            )
            rows, coverage = sets[source].items, sets[source].coverage
            enrichment = None
            notes = []
            if source == "playlist_items":
                rows, enrichment = await self.enrich(
                    principal, rows, sets[source]._detail_reservation
                )
                if enrichment.truncated or enrichment.available < enrichment.selected:
                    notes.append(
                        "Some video details are unavailable or outside the enrichment cap. "
                        "Their item timestamps still count."
                    )
            if source == "liked_videos":
                notes.append(
                    "Dates are when the videos were published, not when they were liked. "
                    "The API exposes only the 1,000 most recent likes."
                )
            if coverage.truncated:
                notes.append(
                    "Partial source coverage: " + (coverage.truncation_reason or "fetch incomplete")
                )
            metrics = analyze(source, rows, request.period, request.compare_to)
            if metrics.excluded_invalid_timestamp:
                notes.append("Items with missing or invalid timestamps were excluded.")
            if metrics.comparison.earlier_count == 0:
                notes.append(
                    "The earlier period has zero valid items. Relative change is undefined."
                )
            reason = None if metrics.count else "No valid items in the requested period."
            if reason:
                notes.append(reason)
            unit, basis = LABELS[source]
            return EngagementResult(
                source=source,
                unit=unit,
                time_basis=basis,
                period=request.period,
                coverage=coverage,
                enrichment=enrichment,
                metrics=metrics,
                qualifiers=notes,
                insufficient_data=reason is not None,
                insufficient_reason=reason,
            )
