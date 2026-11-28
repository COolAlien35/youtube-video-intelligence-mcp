"""Unit tests for QuotaPlanner preflight reservations and batched_lookup_units."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest

from yt_intel.common import AppError, ErrorCode, FakeClock, Principal
from yt_intel.common.request_context import set_request_id
from yt_intel.config import Settings
from yt_intel.quota import QuotaPlan, QuotaPlanner, QuotaService, batched_lookup_units
from yt_intel.storage import get_engine, init_db

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.unit


def _planner(
    tmp_path: Path, *, common_cap: int = 2000, search_cap: int = 20
) -> tuple[QuotaPlanner, QuotaService, FakeClock]:
    settings = Settings(
        _env_file=None,
        data_dir=tmp_path,
        quota_common_daily_cap=common_cap,
        quota_search_daily_cap=search_cap,
    )
    engine = get_engine(settings)
    init_db(engine)
    clock = FakeClock(datetime(2026, 11, 27, 18, 0, tzinfo=UTC))
    service = QuotaService(engine, settings, clock=clock)
    return QuotaPlanner(service), service, clock


def test_batched_lookup_units() -> None:
    """batched_lookup_units rounds up in 50-ID batches and validates inputs."""
    assert batched_lookup_units(0) == 0
    assert batched_lookup_units(1) == 1
    assert batched_lookup_units(50) == 1
    assert batched_lookup_units(51) == 2
    assert batched_lookup_units(100) == 2
    with pytest.raises(ValueError, match="n_ids"):
        batched_lookup_units(-1)
    with pytest.raises(ValueError, match="batch"):
        batched_lookup_units(10, batch=0)


def test_preflight_rejects_over_budget_before_provider_and_logs(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Over-budget plan raises QUOTA_EXCEEDED with zero provider calls and logs safely."""
    planner, service, _ = _planner(tmp_path, common_cap=150, search_cap=1)
    principal = Principal(issuer="https://issuer.example", subject="alice-secret-sub")
    provider_calls = 0

    set_request_id("req-preflight-1")
    try:
        with caplog.at_level(logging.WARNING), pytest.raises(AppError) as exc_info:
            planner.reserve(principal, QuotaPlan(common_units=200, search_calls=1))
        assert exc_info.value.code is ErrorCode.QUOTA_EXCEEDED
        assert exc_info.value.retryable is True
        assert provider_calls == 0
    finally:
        set_request_id(None)

    assert "alice-secret-sub" not in caplog.text
    assert any(rec.message == "quota_preflight_rejected" for rec in caplog.records)
    snap = service.remaining()
    assert snap.common_used == 0
    assert snap.search_used == 0


def test_preflight_commit_and_release_and_pacific_reset(tmp_path: Path) -> None:
    """commit returns unused units; release returns all; Pacific midnight resets."""
    planner, service, clock = _planner(tmp_path, common_cap=300, search_cap=2)
    principal = Principal(issuer="https://issuer.example", subject="alice")

    res = planner.reserve(principal, QuotaPlan(common_units=200, search_calls=2))
    res.commit(QuotaPlan(common_units=102, search_calls=1))
    snap = service.remaining()
    assert snap.common_used == 102
    assert snap.search_used == 1

    res2 = planner.reserve(principal, QuotaPlan(common_units=100, search_calls=1))
    res2.release()
    snap2 = service.remaining()
    assert snap2.common_used == 102
    assert snap2.search_used == 1

    # Advance past next Pacific midnight (18:00 UTC -> 08:01 UTC next day = 14h 1m)
    clock.advance(14 * 3600 + 60)
    snap3 = service.remaining()
    assert snap3.common_used == 0
    assert snap3.search_used == 0
