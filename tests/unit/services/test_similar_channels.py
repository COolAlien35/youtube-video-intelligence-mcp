from collections import Counter

import pytest

from yt_intel.common import AppError, ErrorCode, Principal
from yt_intel.common.errors import RateLimitedError
from yt_intel.quota import PrincipalLimiter, QuotaPlanner, QuotaService
from yt_intel.services.channel_ranking import RankingEngine
from yt_intel.services.similar_channels import ChannelResultCache, SimilarChannelsService
from yt_intel.storage import get_engine, init_db

OWNER = Principal("synthetic", "one")
OTHER = Principal("synthetic", "two")


@pytest.fixture
def workflow(tmp_path, settings_factory, fixture_provider, frozen_clock):
    settings = settings_factory(data_dir=tmp_path)
    engine = get_engine(settings)
    init_db(engine)
    quota = QuotaService(engine, settings, frozen_clock)
    service = SimilarChannelsService(
        fixture_provider,
        QuotaPlanner(quota),
        PrincipalLimiter(engine, settings, frozen_clock),
        ChannelResultCache(engine, frozen_clock),
        RankingEngine(),
    )
    yield service, fixture_provider, quota
    engine.dispose()


async def test_discovery_isolated_cache_expiry_and_ranking(workflow, frozen_clock):
    service, provider, quota = workflow
    result = await service.run(OWNER, "@SYN_Prism")
    ids = [item.id for item in result.items]
    assert len(set(ids)) == result.candidates_considered == 4
    assert result.seed.id not in ids and all(i.explanation for i in result.items)
    assert ids == [i.id for i in sorted(result.items, key=lambda i: (-i.score, i.id))]
    assert "synthetic lens" in " ".join(i.title.lower() for i in result.items)
    assert result.items[0].score > result.items[-1].score
    assert result.pool_limit == 50 and result.pool_limited and result.source.startswith("YouTube")
    initial = Counter(resolve_channel=1, search_channels=1, get_channels=1)
    assert provider.calls == initial
    assert quota.remaining().common_used == 102
    assert await service.run(OWNER, result.seed.id) == result and provider.calls == initial
    assert (
        await service.run(OTHER, result.seed.id) == result and provider.calls == initial + initial
    )
    frozen_clock.advance(86400)
    assert await service.run(OWNER, "@syn_prism") == result
    assert provider.calls == initial + initial + initial


@pytest.mark.parametrize(
    ("handle", "reason"),
    [("@syn_remote", "no_candidates_found"), ("@syn_quiet", "all_candidates_excluded")],
)
async def test_empty_results(workflow, handle, reason):
    service, _, _ = workflow
    result = await service.run(OWNER, handle)
    assert result.items == [] and result.empty_reason == reason and result.empty_explanation


async def test_unknown_handle_never_substitutes_same_display_name(workflow):
    service, provider, quota = workflow
    with pytest.raises(AppError) as exc:
        await service.run(OWNER, "@SyntheticPrismStudio")
    assert exc.value.code == ErrorCode.NOT_FOUND_OR_UNAVAILABLE
    assert provider.calls == {"resolve_channel": 1}
    assert quota.remaining().common_used == 1 and quota.remaining().search_used == 0


async def test_budget_and_concurrency_reject_before_provider(workflow):
    service, provider, _quota = workflow
    with service.limiter.acquire_workflow(OWNER), service.limiter.acquire_workflow(OWNER):
        with pytest.raises(RateLimitedError) as denied:
            await service.run(OWNER, "@syn_prism")
        assert denied.value.retry_after_seconds == denied.value.to_dict()["retry_after"]
        assert not provider.calls
    from yt_intel.quota import QuotaPlan

    reserved = service.planner.reserve(OWNER, QuotaPlan(0, 20))
    try:
        with pytest.raises(AppError) as exc:
            await service.run(OWNER, "@syn_prism")
        assert exc.value.code == ErrorCode.QUOTA_EXCEEDED and not provider.calls
    finally:
        reserved.release()
