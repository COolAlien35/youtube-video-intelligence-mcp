"""Unit and integration tests for the quota ledger."""

from __future__ import annotations

import threading
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest
from yt_intel.common import AppError, ErrorCode, FakeClock

from yt_intel.config import Settings
from yt_intel.quota import QuotaService, WorkflowCost, cost_of
from yt_intel.storage import get_engine, init_db

if TYPE_CHECKING:
    from pathlib import Path

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_service(
    tmp_path: Path,
    *,
    common_cap: int = 100,
    search_cap: int = 10,
    clock: FakeClock | None = None,
) -> QuotaService:
    settings = Settings(
        _env_file=None,
        data_dir=tmp_path / "data",
        quota_common_daily_cap=common_cap,
        quota_search_daily_cap=search_cap,
    )
    engine = get_engine(settings)
    init_db(engine)
    return QuotaService(engine, settings, clock=clock)


_UTC_NOON_NOV_26 = datetime(2026, 11, 26, 20, 0, 0, tzinfo=UTC)  # 12:00 Pacific (PST = UTC-8)
_UTC_NOV_26_MIDNIGHT_PST = datetime(2026, 11, 27, 8, 0, 0, tzinfo=UTC)  # 00:00 Pacific next day


# ---------------------------------------------------------------------------
# cost_of tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_cost_of_videos_list() -> None:
    assert cost_of("videos.list") == WorkflowCost(common_units=1)


@pytest.mark.unit
def test_cost_of_channels_list() -> None:
    assert cost_of("channels.list") == WorkflowCost(common_units=1)


@pytest.mark.unit
def test_cost_of_playlists_insert() -> None:
    assert cost_of("playlists.insert") == WorkflowCost(common_units=50)


@pytest.mark.unit
def test_cost_of_playlist_items_insert_per_item() -> None:
    assert cost_of("playlistItems.insert", count=3) == WorkflowCost(common_units=150)


@pytest.mark.unit
def test_cost_of_search_list_burns_both_buckets() -> None:
    c = cost_of("search.list")
    assert c.search_calls == 1
    assert c.common_units == 100


@pytest.mark.unit
def test_cost_of_unknown_raises() -> None:
    with pytest.raises(ValueError, match="Unknown"):
        cost_of("unknown.operation")


@pytest.mark.unit
def test_cost_of_zero_count_raises() -> None:
    with pytest.raises(ValueError, match="positive"):
        cost_of("videos.list", count=0)


# ---------------------------------------------------------------------------
# WorkflowCost validation
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_workflow_cost_rejects_negative() -> None:
    with pytest.raises(ValueError):
        WorkflowCost(common_units=-1)
    with pytest.raises(ValueError):
        WorkflowCost(search_calls=-1)


# ---------------------------------------------------------------------------
# Pacific-midnight quota day
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_pacific_quota_day_uses_la_midnight(tmp_path: Path) -> None:
    """Quota day should be the LA date, not the UTC date."""
    from yt_intel.quota.service import _pacific_today

    # 23:30 UTC on Nov 26 = 15:30 PST Nov 26 — still Nov 26 in LA
    utc_dt = datetime(2026, 11, 26, 23, 30, tzinfo=UTC)
    assert _pacific_today(utc_dt).isoformat() == "2026-11-26"


@pytest.mark.unit
def test_pacific_quota_day_advances_at_la_midnight(tmp_path: Path) -> None:
    """At 08:01 UTC Nov 27 (PST+8), quota day should flip to Nov 27."""
    from yt_intel.quota.service import _pacific_today

    utc_dt = datetime(2026, 11, 27, 8, 1, tzinfo=UTC)
    assert _pacific_today(utc_dt).isoformat() == "2026-11-27"


@pytest.mark.unit
def test_quota_resets_at_pacific_midnight(tmp_path: Path) -> None:
    """Reservations on day N do not count against day N+1 after a midnight rollover."""
    clock = FakeClock(start=_UTC_NOON_NOV_26)
    svc = _make_service(tmp_path, common_cap=10, clock=clock)

    svc.reserve("iss|alice", "wf-1", WorkflowCost(common_units=10))
    snapshot_day1 = svc.remaining()
    assert snapshot_day1.common_remaining == 0

    # Advance past Pacific midnight
    clock.advance(_next_pacific_midnight_seconds(clock.now()) + 60)
    snapshot_day2 = svc.remaining()
    assert snapshot_day2.common_remaining == 10


@pytest.mark.unit
def test_pacific_midnight_on_dst_transition(tmp_path: Path) -> None:
    """DST transition: 2026-03-08 02:00 PST → PDT (UTC-7). Midnight UTC offset changes."""
    # 2026-03-09 07:01 UTC = 00:01 PDT (UTC-7) → new quota day Mar 9
    utc_after_dst = datetime(2026, 3, 9, 7, 1, tzinfo=UTC)
    from yt_intel.quota.service import _pacific_today

    assert _pacific_today(utc_after_dst).isoformat() == "2026-03-09"


# ---------------------------------------------------------------------------
# Reserve / settle / release
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_reserve_success(tmp_path: Path) -> None:
    clock = FakeClock(start=_UTC_NOON_NOV_26)
    svc = _make_service(tmp_path, common_cap=100, clock=clock)

    res = svc.reserve("iss|alice", "wf-1", WorkflowCost(common_units=30))
    assert res.principal_key == "iss|alice"
    assert res.cost.common_units == 30

    snap = svc.remaining()
    assert snap.common_used == 30
    assert snap.common_remaining == 70


@pytest.mark.unit
def test_over_budget_rejected_and_ledger_unchanged(tmp_path: Path) -> None:
    """An over-budget reservation must raise QUOTA_EXCEEDED and leave the ledger unchanged."""
    clock = FakeClock(start=_UTC_NOON_NOV_26)
    svc = _make_service(tmp_path, common_cap=50, clock=clock)

    svc.reserve("iss|alice", "wf-1", WorkflowCost(common_units=50))
    snap_before = svc.remaining()

    with pytest.raises(AppError) as exc_info:
        svc.reserve("iss|alice", "wf-2", WorkflowCost(common_units=1))

    assert exc_info.value.code == ErrorCode.QUOTA_EXCEEDED
    assert exc_info.value.retryable is True
    assert exc_info.value.retry_after is not None
    assert exc_info.value.retry_after > 0

    snap_after = svc.remaining()
    assert snap_after.common_used == snap_before.common_used


@pytest.mark.unit
def test_settle_moves_reserved_to_used(tmp_path: Path) -> None:
    clock = FakeClock(start=_UTC_NOON_NOV_26)
    svc = _make_service(tmp_path, common_cap=100, clock=clock)

    res = svc.reserve("iss|alice", "wf-1", WorkflowCost(common_units=40))
    svc.settle(res, actual=WorkflowCost(common_units=25))

    snap = svc.remaining()
    assert snap.common_remaining == 100 - 25


@pytest.mark.unit
def test_settle_idempotent(tmp_path: Path) -> None:
    clock = FakeClock(start=_UTC_NOON_NOV_26)
    svc = _make_service(tmp_path, common_cap=100, clock=clock)

    res = svc.reserve("iss|alice", "wf-1", WorkflowCost(common_units=10))
    svc.settle(res)
    svc.settle(res)  # second call must not raise or double-count
    assert svc.remaining().common_remaining == 90


@pytest.mark.unit
def test_release_returns_all_reserved_units(tmp_path: Path) -> None:
    clock = FakeClock(start=_UTC_NOON_NOV_26)
    svc = _make_service(tmp_path, common_cap=100, clock=clock)

    res = svc.reserve("iss|alice", "wf-1", WorkflowCost(common_units=60))
    svc.release(res)

    snap = svc.remaining()
    assert snap.common_remaining == 100


@pytest.mark.unit
def test_release_idempotent(tmp_path: Path) -> None:
    clock = FakeClock(start=_UTC_NOON_NOV_26)
    svc = _make_service(tmp_path, common_cap=100, clock=clock)

    res = svc.reserve("iss|alice", "wf-1", WorkflowCost(common_units=30))
    svc.release(res)
    svc.release(res)  # must not raise or corrupt ledger
    assert svc.remaining().common_remaining == 100


@pytest.mark.unit
@pytest.mark.security
def test_search_bucket_capped_independently(tmp_path: Path) -> None:
    """Exhausting the search bucket while common has capacity still rejects."""
    clock = FakeClock(start=_UTC_NOON_NOV_26)
    svc = _make_service(tmp_path, common_cap=10000, search_cap=5, clock=clock)

    for i in range(5):
        svc.reserve("iss|alice", f"wf-{i}", WorkflowCost(search_calls=1))

    with pytest.raises(AppError) as exc_info:
        svc.reserve("iss|alice", "wf-over", WorkflowCost(search_calls=1))
    assert exc_info.value.code == ErrorCode.QUOTA_EXCEEDED


# ---------------------------------------------------------------------------
# Integration: concurrency
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_concurrent_reservations_never_exceed_cap(tmp_path: Path) -> None:
    """8 threads competing for a cap of exactly 4 — exactly 4 succeed."""
    cap = 4
    n_threads = 8
    cost = WorkflowCost(common_units=1)

    clock = FakeClock(start=_UTC_NOON_NOV_26)
    svc = _make_service(tmp_path, common_cap=cap, clock=clock)

    successes: list[bool] = []
    lock = threading.Lock()

    def _try_reserve(i: int) -> None:
        try:
            svc.reserve(f"iss|user{i}", f"wf-{i}", cost)
            with lock:
                successes.append(True)
        except AppError as e:
            if e.code == ErrorCode.QUOTA_EXCEEDED:
                with lock:
                    successes.append(False)
            else:
                raise

    threads = [threading.Thread(target=_try_reserve, args=(i,)) for i in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert sum(successes) == cap
    snap = svc.remaining()
    assert snap.common_used == cap
    assert snap.common_remaining == 0


def _next_pacific_midnight_seconds(now: datetime) -> float:
    """Test helper: seconds until next LA midnight."""
    try:
        from zoneinfo import ZoneInfo
    except ImportError:
        from backports.zoneinfo import ZoneInfo  # type: ignore[no-redef]

    la_tz = ZoneInfo("America/Los_Angeles")
    la_now = now.astimezone(la_tz)
    la_midnight_next = datetime(la_now.year, la_now.month, la_now.day, tzinfo=la_tz) + timedelta(
        days=1
    )
    return max(1, (la_midnight_next - la_now).total_seconds())
