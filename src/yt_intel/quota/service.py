"""Atomic shared quota ledger service (synchronous, SQLite WAL)."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import text

from yt_intel.common import AppError, ErrorCode
from yt_intel.storage import DailyQuotaRecord, session_scope

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Value types (frozen, exported by __init__.py)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WorkflowCost:
    """Cost of a single workflow's quota consumption in both buckets."""

    common_units: int = 0
    search_calls: int = 0

    def __post_init__(self) -> None:
        if self.common_units < 0:
            raise ValueError("common_units must be >= 0")
        if self.search_calls < 0:
            raise ValueError("search_calls must be >= 0")


@dataclass(frozen=True)
class QuotaSnapshot:
    """Point-in-time view of the shared daily quota ledger."""

    quota_day: date
    common_used: int
    common_cap: int
    search_used: int
    search_cap: int

    @property
    def common_remaining(self) -> int:
        return max(0, self.common_cap - self.common_used)

    @property
    def search_remaining(self) -> int:
        return max(0, self.search_cap - self.search_used)


@dataclass(frozen=True)
class QuotaReservation:
    """An active quota reservation that must be settled or released."""

    reservation_id: str
    principal_key: str
    workflow_id: str
    cost: WorkflowCost
    quota_day: date


# ---------------------------------------------------------------------------
# Pacific-midnight helpers
# ---------------------------------------------------------------------------


def _pacific_today(now: datetime) -> date:
    """Return the current quota day in America/Los_Angeles from an aware UTC datetime."""
    try:
        from zoneinfo import ZoneInfo  # Python 3.9+
    except ImportError:
        from backports.zoneinfo import ZoneInfo  # type: ignore[no-redef,import-not-found]

    la_now = now.astimezone(ZoneInfo("America/Los_Angeles"))
    return la_now.date()


def _next_pacific_midnight_seconds(now: datetime) -> int:
    """Return seconds until the next America/Los_Angeles midnight (quota reset)."""
    try:
        from zoneinfo import ZoneInfo
    except ImportError:
        from backports.zoneinfo import ZoneInfo  # type: ignore[no-redef,import-not-found]

    la_tz = ZoneInfo("America/Los_Angeles")
    la_now = now.astimezone(la_tz)
    la_midnight_next = datetime(la_now.year, la_now.month, la_now.day, tzinfo=la_tz) + timedelta(
        days=1
    )
    return max(1, int((la_midnight_next - la_now).total_seconds()))


# ---------------------------------------------------------------------------
# QuotaService
# ---------------------------------------------------------------------------


class QuotaService:
    """Atomic shared quota ledger service.

    All methods are **synchronous**. Async callers should use
    ``anyio.to_thread.run_sync(service.reserve, ...)`` to avoid blocking the
    event loop.

    The shared ledger is indexed by Pacific-midnight quota day. Two independent
    buckets are checked and updated atomically in a single ``BEGIN IMMEDIATE``
    transaction so a concurrent over-budget check can never race past the cap.
    """

    def __init__(
        self,
        engine: Engine,
        settings: Settings,
        clock: Clock | None = None,
    ) -> None:
        from yt_intel.common import SystemClock
        from yt_intel.config import Settings

        if not isinstance(settings, Settings):
            raise TypeError("settings must be a Settings instance")

        self._engine = engine
        self._common_cap = settings.quota_common_daily_cap
        self._search_cap = settings.quota_search_daily_cap
        self._clock: Clock = clock if clock is not None else SystemClock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def reserve(
        self,
        principal_key: str,
        workflow_id: str,
        cost: WorkflowCost,
    ) -> QuotaReservation:
        """Atomically reserve *cost* from the shared daily quota.

        Raises ``AppError(QUOTA_EXCEEDED)`` with ``retryable=True`` and
        ``retry_after`` set to seconds-until-next-Pacific-midnight if either
        bucket would be exceeded.  On rejection the ledger is **unchanged**.
        """
        now = self._clock.now()
        quota_day = _pacific_today(now)
        reservation_id = str(uuid.uuid4())

        with self._engine.begin() as conn:
            # pysqlite does not honour BEGIN IMMEDIATE by default via SQLAlchemy
            # begin(); BEGIN IMMEDIATE must be issued explicitly.
            conn.execute(text("BEGIN IMMEDIATE"))

            row = conn.execute(
                text(
                    "SELECT common_used, common_reserved, "
                    "search_calls_used, search_calls_reserved "
                    "FROM daily_quotas WHERE quota_day = :day"
                ),
                {"day": quota_day.isoformat()},
            ).fetchone()

            if row is None:
                conn.execute(
                    text(
                        "INSERT INTO daily_quotas "
                        "(quota_day, common_used, common_reserved, "
                        "search_calls_used, search_calls_reserved, updated_at) "
                        "VALUES (:day, 0, 0, 0, 0, :ts)"
                    ),
                    {"day": quota_day.isoformat(), "ts": now.isoformat()},
                )
                common_committed = 0
                search_committed = 0
            else:
                common_committed = (row[0] or 0) + (row[1] or 0)
                search_committed = (row[2] or 0) + (row[3] or 0)

            common_would_be = common_committed + cost.common_units
            search_would_be = search_committed + cost.search_calls

            if common_would_be > self._common_cap or search_would_be > self._search_cap:
                retry_after = _next_pacific_midnight_seconds(now)
                logger.warning(
                    "Quota reservation rejected",
                    extra={
                        "principal_key": principal_key,
                        "workflow_id": workflow_id,
                        "common_requested": cost.common_units,
                        "common_committed": common_committed,
                        "common_cap": self._common_cap,
                        "search_requested": cost.search_calls,
                        "search_committed": search_committed,
                        "search_cap": self._search_cap,
                        "retry_after_seconds": retry_after,
                    },
                )
                raise AppError(
                    ErrorCode.QUOTA_EXCEEDED,
                    "Daily quota cap reached",
                    retryable=True,
                    retry_after=retry_after,
                )

            conn.execute(
                text(
                    "UPDATE daily_quotas SET "
                    "common_reserved = common_reserved + :cr, "
                    "search_calls_reserved = search_calls_reserved + :sr, "
                    "updated_at = :ts "
                    "WHERE quota_day = :day"
                ),
                {
                    "cr": cost.common_units,
                    "sr": cost.search_calls,
                    "ts": now.isoformat(),
                    "day": quota_day.isoformat(),
                },
            )
            conn.execute(
                text(
                    "INSERT INTO quota_reservations "
                    "(reservation_id, quota_day, principal_key, workflow_id, "
                    "common_reserved, search_reserved, common_settled, search_settled, state, "
                    "created_at, updated_at) "
                    "VALUES (:rid, :day, :pk, :wid, :cr, :sr, 0, 0, 'reserved', :ts, :ts)"
                ),
                {
                    "rid": reservation_id,
                    "day": quota_day.isoformat(),
                    "pk": principal_key,
                    "wid": workflow_id,
                    "cr": cost.common_units,
                    "sr": cost.search_calls,
                    "ts": now.isoformat(),
                },
            )

        return QuotaReservation(
            reservation_id=reservation_id,
            principal_key=principal_key,
            workflow_id=workflow_id,
            cost=cost,
            quota_day=quota_day,
        )

    def settle(
        self,
        reservation: QuotaReservation,
        actual: WorkflowCost | None = None,
    ) -> None:
        """Move reservation from *reserved* to *used*, returning any unused units.

        Idempotent: settling an already-settled reservation is a no-op.
        *actual* defaults to the full reserved cost.
        """
        actual = actual if actual is not None else reservation.cost
        now = self._clock.now()
        with self._engine.begin() as conn:
            conn.execute(text("BEGIN IMMEDIATE"))
            existing = conn.execute(
                text("SELECT state FROM quota_reservations WHERE reservation_id = :rid"),
                {"rid": reservation.reservation_id},
            ).fetchone()
            if existing is None or existing[0] != "reserved":
                return  # already settled or released — idempotent

            unused_common = max(0, reservation.cost.common_units - actual.common_units)
            unused_search = max(0, reservation.cost.search_calls - actual.search_calls)

            conn.execute(
                text(
                    "UPDATE daily_quotas SET "
                    "common_used = common_used + :au, "
                    "common_reserved = common_reserved - :cr, "
                    "search_calls_used = search_calls_used + :as_, "
                    "search_calls_reserved = search_calls_reserved - :sr, "
                    "updated_at = :ts "
                    "WHERE quota_day = :day"
                ),
                {
                    "au": actual.common_units,
                    "cr": reservation.cost.common_units,
                    "as_": actual.search_calls,
                    "sr": reservation.cost.search_calls,
                    "ts": now.isoformat(),
                    "day": reservation.quota_day.isoformat(),
                },
            )
            conn.execute(
                text(
                    "UPDATE quota_reservations SET "
                    "state = 'settled', "
                    "common_settled = :au, "
                    "search_settled = :as_, "
                    "updated_at = :ts "
                    "WHERE reservation_id = :rid"
                ),
                {
                    "au": actual.common_units,
                    "as_": actual.search_calls,
                    "ts": now.isoformat(),
                    "rid": reservation.reservation_id,
                },
            )
            if unused_common > 0 or unused_search > 0:
                logger.debug(
                    "Quota settle: returned unused units",
                    extra={
                        "reservation_id": reservation.reservation_id,
                        "unused_common": unused_common,
                        "unused_search": unused_search,
                    },
                )

    def release(self, reservation: QuotaReservation) -> None:
        """Return the full reserved cost to the pool without settling.

        Idempotent: releasing an already-released reservation is a no-op.
        """
        now = self._clock.now()
        with self._engine.begin() as conn:
            conn.execute(text("BEGIN IMMEDIATE"))
            existing = conn.execute(
                text("SELECT state FROM quota_reservations WHERE reservation_id = :rid"),
                {"rid": reservation.reservation_id},
            ).fetchone()
            if existing is None or existing[0] != "reserved":
                return  # already released or settled — idempotent

            conn.execute(
                text(
                    "UPDATE daily_quotas SET "
                    "common_reserved = common_reserved - :cr, "
                    "search_calls_reserved = search_calls_reserved - :sr, "
                    "updated_at = :ts "
                    "WHERE quota_day = :day"
                ),
                {
                    "cr": reservation.cost.common_units,
                    "sr": reservation.cost.search_calls,
                    "ts": now.isoformat(),
                    "day": reservation.quota_day.isoformat(),
                },
            )
            conn.execute(
                text(
                    "UPDATE quota_reservations SET state = 'released', updated_at = :ts "
                    "WHERE reservation_id = :rid"
                ),
                {"ts": now.isoformat(), "rid": reservation.reservation_id},
            )

    def remaining(self) -> QuotaSnapshot:
        """Return a snapshot of today's shared quota remaining in both buckets."""
        now = self._clock.now()
        quota_day = _pacific_today(now)

        with session_scope(self._engine) as session:
            row = session.get(DailyQuotaRecord, quota_day)
            if row is None:
                return QuotaSnapshot(
                    quota_day=quota_day,
                    common_used=0,
                    common_cap=self._common_cap,
                    search_used=0,
                    search_cap=self._search_cap,
                )
            common_used = (row.common_used or 0) + (row.common_reserved or 0)
            search_used = (row.search_calls_used or 0) + (row.search_calls_reserved or 0)
            return QuotaSnapshot(
                quota_day=quota_day,
                common_used=common_used,
                common_cap=self._common_cap,
                search_used=search_used,
                search_cap=self._search_cap,
            )


# Forward reference for type hints (resolved at runtime)
from yt_intel.common import Clock  # noqa: E402  # imported after class definition to avoid circular
from yt_intel.config import Settings  # noqa: E402

# Annotate __init__ properly without circular import at module level
QuotaService.__init__.__annotations__["settings"] = Settings
QuotaService.__init__.__annotations__["clock"] = "Clock | None"
