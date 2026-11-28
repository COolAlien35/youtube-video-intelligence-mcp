"""Preflight quota planning and reservation facade over QuotaService."""

from __future__ import annotations

import hashlib
import logging
import uuid
from typing import TYPE_CHECKING

from yt_intel.common.errors import AppError, ErrorCode
from yt_intel.common.request_context import get_request_id
from yt_intel.quota.service import QuotaReservation, QuotaService, WorkflowCost

if TYPE_CHECKING:
    from yt_intel.common.types import Principal

logger = logging.getLogger(__name__)

QuotaPlan = WorkflowCost


def batched_lookup_units(n_ids: int, batch: int = 50) -> int:
    """Return YouTube ``videos.list``/``channels.list`` units for *n_ids* (1 unit per batch)."""
    if n_ids < 0:
        raise ValueError("n_ids must be >= 0")
    if batch <= 0:
        raise ValueError("batch must be > 0")
    if n_ids == 0:
        return 0
    return (n_ids + batch - 1) // batch


class Reservation:
    """Handle for an active preflight reservation that settles or releases."""

    def __init__(self, service: QuotaService, raw: QuotaReservation) -> None:
        self._service = service
        self._raw = raw

    @property
    def reservation_id(self) -> str:
        """Unique reservation identifier."""
        return self._raw.reservation_id

    @property
    def plan(self) -> QuotaPlan:
        """Reserved quota plan."""
        return self._raw.cost

    def commit(self, actual: QuotaPlan) -> None:
        """Settle *actual* usage and return any unused reserved units."""
        self._service.settle(self._raw, actual)

    def release(self) -> None:
        """Release all reserved units back to the shared ledger."""
        self._service.release(self._raw)


class QuotaPlanner:
    """Preflight quota planner enforcing atomic two-bucket reservations."""

    def __init__(self, service: QuotaService) -> None:
        self._service = service

    def reserve(
        self,
        principal: Principal,
        plan: QuotaPlan,
        *,
        workflow_id: str | None = None,
    ) -> Reservation:
        """Atomically reserve *plan* for *principal* or log and raise QUOTA_EXCEEDED."""
        wf_id = workflow_id if workflow_id else str(uuid.uuid4())
        try:
            raw = self._service.reserve(principal.key, wf_id, plan)
        except AppError as exc:
            if exc.code is ErrorCode.QUOTA_EXCEEDED:
                principal_hash = hashlib.sha256(principal.key.encode("utf-8")).hexdigest()[:16]
                logger.warning(
                    "quota_preflight_rejected",
                    extra={
                        "request_id": get_request_id(),
                        "principal_hash": principal_hash,
                        "planned_common": plan.common_units,
                        "planned_search": plan.search_calls,
                        "details": exc.details,
                    },
                )
            raise
        return Reservation(self._service, raw)
