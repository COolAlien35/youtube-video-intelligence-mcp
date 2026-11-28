"""Per-principal concurrency and rolling start-rate limiter backed by SQLite."""

from __future__ import annotations

import math
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import text

from yt_intel.common.clock import Clock, SystemClock
from yt_intel.common.errors import AppError, ErrorCode

if TYPE_CHECKING:
    from collections.abc import Iterator

    from sqlalchemy.engine import Engine

    from yt_intel.common.types import Principal
    from yt_intel.config import Settings

_RATE_WINDOW_SECONDS = 60


class PrincipalLimiter:
    """Enforce per-principal max concurrent workflows and starts-per-minute."""

    def __init__(
        self,
        engine: Engine,
        settings: Settings,
        clock: Clock | None = None,
    ) -> None:
        self._engine = engine
        self._max_concurrent = settings.max_concurrent_workflows_per_principal
        self._max_starts_per_minute = settings.max_workflow_starts_per_minute
        self._clock: Clock = clock if clock is not None else SystemClock()

    @contextmanager
    def acquire_workflow(
        self,
        principal: Principal,
        *,
        workflow_id: str | None = None,
    ) -> Iterator[str]:
        """Acquire a workflow slot for *principal*, releasing it in ``finally``."""
        wf_id = workflow_id if workflow_id else str(uuid.uuid4())
        now = self._clock.now().astimezone(UTC)
        window_start = now - timedelta(seconds=_RATE_WINDOW_SECONDS)
        prune_before = now - timedelta(seconds=_RATE_WINDOW_SECONDS * 2)

        with self._engine.begin() as conn:
            conn.execute(text("BEGIN IMMEDIATE"))

            conn.execute(
                text(
                    "DELETE FROM workflow_limits "
                    "WHERE principal_key = :pk AND active = 0 AND started_at <= :prune_before"
                ),
                {"pk": principal.key, "prune_before": prune_before.isoformat()},
            )

            active_count = conn.execute(
                text(
                    "SELECT COUNT(*) FROM workflow_limits WHERE principal_key = :pk AND active = 1"
                ),
                {"pk": principal.key},
            ).scalar_one()
            if active_count >= self._max_concurrent:
                raise AppError(
                    ErrorCode.RATE_LIMITED,
                    "Too many concurrent workflows for principal",
                    details={"max_concurrent": self._max_concurrent},
                    retryable=True,
                    retry_after=5,
                )

            recent_rows = conn.execute(
                text(
                    "SELECT started_at FROM workflow_limits "
                    "WHERE principal_key = :pk AND started_at > :window_start "
                    "ORDER BY started_at ASC"
                ),
                {"pk": principal.key, "window_start": window_start.isoformat()},
            ).fetchall()

            if len(recent_rows) >= self._max_starts_per_minute:
                oldest_raw = str(recent_rows[0][0])
                oldest_dt = datetime.fromisoformat(oldest_raw)
                if oldest_dt.tzinfo is None:
                    oldest_dt = oldest_dt.replace(tzinfo=UTC)
                elapsed = (now - oldest_dt).total_seconds()
                retry_after = max(1, math.ceil(_RATE_WINDOW_SECONDS - elapsed))
                raise AppError(
                    ErrorCode.RATE_LIMITED,
                    "Workflow start rate limit exceeded for principal",
                    details={"max_starts_per_minute": self._max_starts_per_minute},
                    retryable=True,
                    retry_after=retry_after,
                )

            conn.execute(
                text(
                    "INSERT INTO workflow_limits (principal_key, workflow_id, started_at, active) "
                    "VALUES (:pk, :wf_id, :started_at, 1)"
                ),
                {
                    "pk": principal.key,
                    "wf_id": wf_id,
                    "started_at": now.isoformat(),
                },
            )

        try:
            yield wf_id
        finally:
            with self._engine.begin() as conn:
                conn.execute(
                    text(
                        "UPDATE workflow_limits SET active = 0 "
                        "WHERE principal_key = :pk AND workflow_id = :wf_id"
                    ),
                    {"pk": principal.key, "wf_id": wf_id},
                )
