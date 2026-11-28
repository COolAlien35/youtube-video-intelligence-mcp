"""Unit tests for PrincipalLimiter concurrency and rolling start-rate limits."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest

from yt_intel.common import AppError, ErrorCode, FakeClock, Principal
from yt_intel.config import Settings
from yt_intel.quota import PrincipalLimiter
from yt_intel.storage import get_engine, init_db

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.unit


def _limiter(tmp_path: Path) -> tuple[PrincipalLimiter, FakeClock]:
    settings = Settings(_env_file=None, data_dir=tmp_path)
    engine = get_engine(settings)
    init_db(engine)
    clock = FakeClock(datetime(2026, 11, 27, 12, 0, tzinfo=UTC))
    return PrincipalLimiter(engine, settings, clock=clock), clock


def test_concurrency_limit_and_exception_release(tmp_path: Path) -> None:
    """Third concurrent workflow is rejected; slots are freed on exit or exception."""
    limiter, _ = _limiter(tmp_path)
    alice = Principal(issuer="https://issuer.example", subject="alice")
    bob = Principal(issuer="https://issuer.example", subject="bob")

    with limiter.acquire_workflow(alice), limiter.acquire_workflow(alice):
        with pytest.raises(AppError) as exc_info, limiter.acquire_workflow(alice):
            pass
        assert exc_info.value.code is ErrorCode.RATE_LIMITED
        assert exc_info.value.retryable is True

        # Independent principal is unaffected
        with limiter.acquire_workflow(bob):
            pass

    # Exception inside workflow still releases the slot
    with pytest.raises(RuntimeError, match="boom"), limiter.acquire_workflow(alice):
        raise RuntimeError("boom")

    with limiter.acquire_workflow(alice):
        pass


def test_rolling_starts_per_minute_limit_and_recovery(tmp_path: Path) -> None:
    """Sixth start within 60s is rejected; advancing clock 60s restores capacity."""
    limiter, clock = _limiter(tmp_path)
    alice = Principal(issuer="https://issuer.example", subject="alice")

    for _ in range(5):
        with limiter.acquire_workflow(alice):
            pass

    with pytest.raises(AppError) as exc_info, limiter.acquire_workflow(alice):
        pass
    assert exc_info.value.code is ErrorCode.RATE_LIMITED
    assert exc_info.value.retry_after == 60

    clock.advance(60)
    with limiter.acquire_workflow(alice):
        pass
