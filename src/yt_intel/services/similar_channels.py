"""Fixture-backed FR-2 discovery with exact seed resolution and atomic preflight."""

import json
from datetime import timedelta
from typing import Literal

from anyio import to_thread
from fastapi.concurrency import contextmanager_in_threadpool
from pydantic import BaseModel
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.engine import Engine

from yt_intel.common import AppError, Clock, ErrorCode, Principal, SystemClock
from yt_intel.common.ids import ChannelRef, parse_channel_ref
from yt_intel.provider.base import YouTubeProvider
from yt_intel.provider.models import Channel
from yt_intel.quota import PrincipalLimiter, QuotaPlan, QuotaPlanner, batched_lookup_units
from yt_intel.quota.costs import cost_of
from yt_intel.storage import session_scope
from yt_intel.storage.models import CacheEntryRecord

from .channel_ranking import Document, RankingEngine, WeightProfile

POOL = 50
WEIGHTS = WeightProfile(0.40, 0.40, 0.20, 0)
TTL = timedelta(hours=24)
KIND = "similar_channels_v1"


class ChannelSummary(BaseModel):
    id: str
    title: str
    canonical_link: str


class SimilarChannel(ChannelSummary):
    score: float
    explanation: str


class SimilarChannelsResult(BaseModel):
    seed: ChannelSummary
    items: list[SimilarChannel]
    candidates_considered: int
    pool_limited: bool = True
    pool_limit: int = POOL
    empty_reason: Literal["no_candidates_found", "all_candidates_excluded"] | None = None
    empty_explanation: str | None = None
    provenance: str = (
        "Similarity reflects channel metadata. It does not assess quality or accuracy."
    )
    source: str = "YouTube (synthetic fixture data)"


def _summary(channel: Channel) -> ChannelSummary:
    return ChannelSummary(
        id=channel.id,
        title=channel.title,
        canonical_link=f"https://www.youtube.com/channel/{channel.id}",
    )


def _document(channel: Channel) -> Document:
    return Document(channel.id, channel.title, channel.description, channel.keywords)


class ChannelResultCache:
    """Canonical result rows on the existing tenant-scoped SQLite cache table."""

    def __init__(self, engine: Engine, clock: Clock | None = None) -> None:
        self.engine = engine
        self.clock = clock or SystemClock()

    def get(self, principal: Principal, ref: ChannelRef) -> SimilarChannelsResult | None:
        row = CacheEntryRecord
        now = self.clock.now()
        match = (
            row.canonical_resource_id == ref.value
            if ref.kind == "id"
            else func.json_extract(row.payload, "$.handle") == ref.value.casefold()
        )
        with session_scope(self.engine) as session:
            session.execute(delete(row).where(row.category == KIND, row.expires_at <= now))
            payload = session.scalar(
                select(row.payload)
                .where(
                    row.category == KIND,
                    row.account_ref == "",
                    row.principal_key == principal.key,
                    row.expires_at > now,
                    row.fetched_at > now - TTL,
                    match,
                )
                .order_by(row.fetched_at.desc())
                .limit(1)
            )
        return (
            SimilarChannelsResult.model_validate(json.loads(payload)["result"]) if payload else None
        )

    def put(self, principal: Principal, seed: Channel, result: SimilarChannelsResult) -> None:
        now = self.clock.now()
        values = {
            "fetched_at": now,
            "expires_at": now + TTL,
            "payload": json.dumps(
                {"handle": (seed.handle or "").casefold(), "result": result.model_dump()}
            ),
        }
        stmt = insert(CacheEntryRecord).values(
            principal_key=principal.key,
            category=KIND,
            canonical_resource_id=seed.id,
            account_ref="",
            **values,
        )
        with session_scope(self.engine) as session:
            session.execute(
                stmt.on_conflict_do_update(
                    index_elements=[
                        "principal_key",
                        "category",
                        "canonical_resource_id",
                        "account_ref",
                    ],
                    set_=values,
                )
            )


class SimilarChannelsService:
    def __init__(
        self,
        provider: YouTubeProvider,
        planner: QuotaPlanner,
        limiter: PrincipalLimiter,
        cache: ChannelResultCache,
        ranker: RankingEngine,
    ) -> None:
        self.provider = provider
        self.planner = planner
        self.limiter = limiter
        self.cache = cache
        self.ranker = ranker

    async def run(self, principal: Principal, channel_ref: str) -> SimilarChannelsResult:
        ref = parse_channel_ref(channel_ref)
        async with contextmanager_in_threadpool(self.limiter.acquire_workflow(principal)):
            cached = await to_thread.run_sync(self.cache.get, principal, ref)
            if cached is not None:
                return cached
            search = cost_of("search.list")
            plan = QuotaPlan(
                1 + search.common_units + batched_lookup_units(POOL), search.search_calls
            )
            reservation = await to_thread.run_sync(self.planner.reserve, principal, plan)
            common, searches = 1, 0
            try:
                seed = await self.provider.resolve_channel(ref)
                if (
                    seed is None
                    or (ref.kind == "id" and seed.id != ref.value)
                    or (
                        ref.kind == "handle"
                        and (seed.handle or "").casefold() != ref.value.casefold()
                    )
                ):
                    raise AppError(ErrorCode.NOT_FOUND_OR_UNAVAILABLE, "Exact channel unavailable")
                query = " ".join(
                    dict.fromkeys(" ".join((seed.title, *seed.keywords)).casefold().split())
                )[:200]
                common += search.common_units
                searches += search.search_calls
                page = await self.provider.search_channels(query, max_results=POOL, page_token=None)
                pool = page.channel_ids[:POOL]
                ids = list(dict.fromkeys(i for i in pool if i != seed.id))
                channels: dict[str, Channel] = {}
                if ids:
                    common += batched_lookup_units(len(ids))
                    batch = await self.provider.get_channels(ids)
                    channels = {
                        c.id: c
                        for c in batch.channels
                        if c.id in ids and c.id not in batch.unavailable_ids
                    }
            finally:
                reservation.commit(QuotaPlan(common, searches))
            ranked = self.ranker.rank(
                _document(seed), [_document(c) for c in channels.values()], weights=WEIGHTS
            )
            items = []
            for item in ranked:
                fields = ", ".join(
                    f"{field} {value / item.score:.0%}"
                    for field, value in item.factors.items()
                    if value > 0
                )
                explanation = (
                    f"Shared terms: {', '.join(item.top_terms)}. Score contributions: {fields}."
                    if item.score
                    else "No shared terms in the available metadata."
                )
                items.append(
                    SimilarChannel(
                        **_summary(channels[item.id]).model_dump(),
                        score=item.score,
                        explanation=explanation,
                    )
                )
            result = SimilarChannelsResult(
                seed=_summary(seed), items=items, candidates_considered=len(channels)
            )
            if not items:
                result.empty_reason = "all_candidates_excluded" if pool else "no_candidates_found"
                result.empty_explanation = (
                    "The search page contained only the seed or unavailable channels."
                    if pool
                    else "The bounded channel search returned no candidates."
                )
            await to_thread.run_sync(self.cache.put, principal, seed, result)
            return result
