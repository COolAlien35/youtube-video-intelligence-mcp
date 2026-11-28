"""Concurrency tests for QuotaPlanner atomic two-bucket reservations (TQ-33)."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest

from yt_intel.common import AppError, ErrorCode, FakeClock, Principal
from yt_intel.config import Settings
from yt_intel.quota import QuotaPlan, QuotaPlanner, QuotaService
from yt_intel.storage import get_engine, init_db

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.unit


def test_preflight_concurrent_reservations_never_exceed_caps(tmp_path: Path) -> None:
    """Multiple concurrent threads racing on the last units never exceed either cap."""
    settings = Settings(
        _env_file=None,
        data_dir=tmp_path,
        quota_common_daily_cap=500,
        quota_search_daily_cap=5,
    )
    engine = get_engine(settings)
    init_db(engine)
    clock = FakeClock(datetime(2026, 11, 27, 18, 0, tzinfo=UTC))
    service = QuotaService(engine, settings, clock=clock)
    planner = QuotaPlanner(service)
    principal = Principal(issuer="https://issuer.example", subject="alice")

    def attempt(idx: int) -> bool:
        try:
            res = planner.reserve(
                principal,
                QuotaPlan(common_units=100, search_calls=1),
                workflow_id=f"wf-{idx}",
            )
            res.commit(QuotaPlan(common_units=100, search_calls=1))
        except AppError as exc:
            assert exc.code is ErrorCode.QUOTA_EXCEEDED
            return False
        return True

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(attempt, range(12)))

    assert sum(1 for ok in results if ok) == 5
    snap = service.remaining()
    assert snap.common_used == 500
    assert snap.search_used == 5
