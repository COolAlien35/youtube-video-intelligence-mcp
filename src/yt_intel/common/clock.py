"""Clock protocol and implementations — §0.4 interface contract (stub for D's implementation)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol


class Clock(Protocol):
    """Time source; pass a FakeClock in tests to control time."""

    def now(self) -> datetime:
        """Return the current UTC-aware datetime."""
        ...


class SystemClock:
    """Production clock — returns the real UTC time."""

    def now(self) -> datetime:
        return datetime.now(UTC)


class FakeClock:
    """Deterministic clock for tests."""

    def __init__(self, start: datetime) -> None:
        if start.tzinfo is None:
            raise ValueError("FakeClock start must be timezone-aware")
        self._now = start

    def now(self) -> datetime:
        return self._now

    def advance(self, seconds: float) -> None:
        """Advance the clock by *seconds* (may be fractional)."""
        from datetime import timedelta

        self._now = self._now + timedelta(seconds=seconds)
