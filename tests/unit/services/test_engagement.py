from datetime import UTC, datetime

import pytest

from yt_intel.analytics.engine import Observation, Window
from yt_intel.common import AppError, ErrorCode, Principal
from yt_intel.config import Settings
from yt_intel.quota import PrincipalLimiter, QuotaPlan, QuotaPlanner, QuotaService
from yt_intel.services.engagement import (
    LABELS,
    Coverage,
    EngagementRequest,
    EngagementService,
    LoadedSignals,
)
from yt_intel.storage import get_engine, init_db

OWNER = Principal("synthetic", "user")
NOW = datetime(2026, 1, 1, tzinfo=UTC)
PERIOD = Window(NOW, datetime(2026, 2, 1, tzinfo=UTC))


class SyntheticLoader:
    def __init__(self):
        self.rows = [Observation(NOW)]

    async def load(self, principal, want, *, playlist_ids=(), like_cap=1000):
        if principal != OWNER:
            raise AppError(ErrorCode.AUTH_EXPIRED_OR_REVOKED, "Reconnect the Google account")
        (source,) = want
        return {
            source: LoadedSignals(
                items=self.rows,
                coverage=Coverage(
                    source=source,
                    unit=LABELS[source][0],
                    time_basis=LABELS[source][1],
                    fetched_count=len(self.rows),
                    reported_total=None,
                    cap=1000,
                    truncated=True,
                    truncation_reason="partial fetch",
                    from_cache=True,
                    fetched_at=NOW,
                ),
            )
        }


@pytest.fixture
def service(tmp_path, fixture_provider):
    settings = Settings(_env_file=None, data_dir=tmp_path)
    engine = get_engine(settings)
    init_db(engine)
    yield EngagementService(
        SyntheticLoader(),
        fixture_provider,
        engine,
        QuotaPlanner(QuotaService(engine, settings)),
        PrincipalLimiter(engine, settings),
    )
    engine.dispose()


@pytest.mark.parametrize("source", list(LABELS))
async def test_labels_and_partial(service, source):
    req = EngagementRequest(
        source=source, period=PERIOD, playlist_id="PLSYN" if source == "playlist_items" else None
    )
    result = await service.run(OWNER, req)
    assert (result.unit, result.time_basis) == LABELS[source] and result.timezone == "UTC"
    assert result.coverage.truncated and result.coverage.from_cache and result.metrics.count == 1
    if source == "liked_videos":
        assert any("1,000" in q and "published" in q for q in result.qualifiers)
    service.loader.rows = [Observation(None)]
    empty = await service.run(OWNER, req)
    assert empty.insufficient_data and empty.insufficient_reason


async def test_playlist_batch_cost_cache_and_rejection(service):
    ids = list(service.provider.videos)[:51]
    assert len(ids) == 51
    service.loader.rows = [Observation(NOW, video_id=vid) for vid in ids]
    req = EngagementRequest(source="playlist_items", playlist_id="PLSYN", period=PERIOD)
    hold = service.planner.reserve(OWNER, QuotaPlan(2000))
    try:
        with pytest.raises(AppError) as exc:
            await service.run(OWNER, req)
        assert exc.value.code == ErrorCode.QUOTA_EXCEEDED and not service.provider.calls
    finally:
        hold.release()
    first = await service.run(OWNER, req)
    assert first.enrichment.available == 51 and service.provider.calls["get_videos"] == 2
    assert await service.run(OWNER, req) == first and service.provider.calls["get_videos"] == 2


async def test_denial_and_limiter(service):
    req = EngagementRequest(source="liked_videos", period=PERIOD)
    with pytest.raises(AppError) as exc:
        await service.run(Principal("synthetic", "other"), req)
    assert exc.value.code == ErrorCode.AUTH_EXPIRED_OR_REVOKED
    with service.limiter.acquire_workflow(OWNER), service.limiter.acquire_workflow(OWNER):
        with pytest.raises(AppError) as limited:
            await service.run(OWNER, req)
        assert limited.value.code == ErrorCode.RATE_LIMITED
    assert not service.provider.calls
