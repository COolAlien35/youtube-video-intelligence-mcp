"""Bounded, fixture-backed video discovery with principal-scoped result caching."""

import re
import unicodedata
from dataclasses import asdict
from typing import Literal

from fastapi.concurrency import contextmanager_in_threadpool
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.engine import Engine

from yt_intel.cache.store import CacheStore
from yt_intel.common import Principal
from yt_intel.common.ids import parse_video_id
from yt_intel.provider.base import YouTubeProvider
from yt_intel.provider.models import VideoMetadata
from yt_intel.quota import PrincipalLimiter, QuotaPlan, QuotaPlanner, batched_lookup_units, cost_of
from yt_intel.storage import session_scope
from yt_intel.storage.scoped import ScopedSession

from .channel_ranking import Document, RankedItem, VideoRankingEngine
from .video_seed import resolve_seed

POOL = 50
CACHE_KIND = "similar_videos_v1"


class VideoRef(BaseModel):
    id: str
    title: str
    canonical_link: str


class RankedVideo(VideoRef):
    channel_title: str | None
    duration_seconds: int | None
    score: float
    explanation: str


class SimilarVideosResult(BaseModel):
    seed: VideoRef
    items: list[RankedVideo]
    candidates_considered: int
    pool_limit: int = POOL
    pool_limited: bool = True
    weights_applied: dict[str, float]
    empty_reason: Literal["no_candidates_found", "all_candidates_excluded"] | None = None
    empty_explanation: str | None = None
    source: str = "YouTube (synthetic fixture data)"
    provenance: str = "Similarity measures metadata overlap. Quality and accuracy are not assessed."


def search_query(seed: VideoMetadata) -> str:
    parts = (seed.title, *(seed.tags or ())[:3])
    terms = re.findall(r"[^\W_]+", unicodedata.normalize("NFKC", " ".join(parts)).casefold())
    return " ".join(dict.fromkeys(terms))[:160].strip()


def _ref(video: VideoMetadata) -> VideoRef:
    return VideoRef(
        id=video.id, title=video.title, canonical_link=f"https://www.youtube.com/watch?v={video.id}"
    )


def _doc(video: VideoMetadata) -> Document:
    return Document(video.id, video.title, video.description, video.tags or (), video.category_id)


def _explain(item: RankedItem) -> str:
    if not item.score:
        return "No matching metadata signals in this candidate pool."
    terms = [term for term in item.top_terms if term.isalnum() and len(term) <= 24][:3]
    fields = ", ".join(
        f"{field} {value / item.score:.0%}"
        for field, value in item.factors.items()
        if field in {"title", "description", "keywords", "category", "tags"} and value > 0
    )
    message = f"Score contributions: {fields}."
    return (message + (" Shared terms: " + ", ".join(terms) + "." if terms else ""))[:240]


class SimilarVideosService:
    def __init__(
        self,
        provider: YouTubeProvider,
        planner: QuotaPlanner,
        limiter: PrincipalLimiter,
        engine: Engine,
        ranker: VideoRankingEngine,
    ) -> None:
        self.provider = provider
        self.planner = planner
        self.limiter = limiter
        self.engine = engine
        self.ranker = ranker

    async def run(self, principal: Principal, video_ref: str) -> SimilarVideosResult:
        seed_id = parse_video_id(video_ref)
        async with contextmanager_in_threadpool(self.limiter.acquire_workflow(principal)):
            with session_scope(self.engine) as session:
                hit = CacheStore(ScopedSession(session, principal)).get(CACHE_KIND, seed_id)
            if hit:
                return SimilarVideosResult.model_validate(hit.value)
            search = cost_of("search.list")
            reservation = self.planner.reserve(
                principal,
                QuotaPlan(
                    1 + search.common_units + batched_lookup_units(POOL), search.search_calls
                ),
            )
            common, searches = 1, 0
            try:
                seed = await resolve_seed(self.provider, seed_id)
                query = search_query(seed)
                pool: tuple[str, ...] = ()
                if query:
                    common += search.common_units
                    searches += search.search_calls
                    page = await self.provider.search_videos(
                        query, max_results=POOL, page_token=None
                    )
                    pool = page.video_ids[:POOL]
                ids = list(
                    dict.fromkeys(
                        i for i in pool if i != seed_id and re.fullmatch(r"[\w-]{11}", i, re.ASCII)
                    )
                )
                videos: dict[str, VideoMetadata] = {}
                if ids:
                    common += batched_lookup_units(len(ids))
                    batch = await self.provider.get_videos(ids)
                    videos = {
                        v.id: v
                        for v in batch.videos
                        if v.id in ids and v.id not in batch.unavailable_ids
                    }
            finally:
                reservation.commit(QuotaPlan(common, searches))
            document = _doc(seed)
            weights = self.ranker.weights_for(document)
            ranked = self.ranker.rank(document, [_doc(v) for v in videos.values()], weights=weights)
            items = [
                RankedVideo(
                    **_ref(videos[r.id]).model_dump(),
                    channel_title=videos[r.id].channel_title,
                    duration_seconds=videos[r.id].duration_seconds,
                    score=r.score,
                    explanation=_explain(r),
                )
                for r in ranked
            ]
            result = SimilarVideosResult(
                seed=_ref(seed),
                items=items,
                candidates_considered=len(videos),
                weights_applied=asdict(weights),
            )
            if not items:
                result.empty_reason = "all_candidates_excluded" if pool else "no_candidates_found"
                result.empty_explanation = (
                    "All returned references were excluded or unavailable."
                    if pool
                    else "No candidates were found in the bounded search."
                )
            with session_scope(self.engine) as session:
                session.execute(text("BEGIN IMMEDIATE"))
                CacheStore(ScopedSession(session, principal)).put(
                    CACHE_KIND, seed_id, result.model_dump(mode="json")
                )
            return result
