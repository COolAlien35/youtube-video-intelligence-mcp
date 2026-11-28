"""Operation types, state enums, quota estimator, and structural protocols (Phase 6)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from yt_intel.common.errors import AppError, ErrorCode

if TYPE_CHECKING:
    from datetime import datetime

    from yt_intel.common.types import Principal

_CREATE_PLAYLIST_UNITS = 50
_INSERT_ITEM_UNITS = 50


def estimate_write_units(n_items: int) -> int:
    """Return planned common quota units for creating a playlist with *n_items* videos."""
    if n_items < 0:
        raise ValueError("n_items must be >= 0")
    return _CREATE_PLAYLIST_UNITS + _INSERT_ITEM_UNITS * n_items


class OperationState(StrEnum):
    """Lifecycle states of an external playlist write operation."""

    CREATING = "CREATING"
    PARTIALLY_COMPLETED = "PARTIALLY_COMPLETED"
    OUTCOME_UNCERTAIN = "OUTCOME_UNCERTAIN"
    RECONCILIATION = "RECONCILIATION"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ItemOutcome(StrEnum):
    """Per-item journal outcome."""

    PENDING = "PENDING"
    INSERTING = "INSERTING"
    INSERTED = "INSERTED"
    FAILED = "FAILED"
    UNCERTAIN = "UNCERTAIN"


class ReconciliationOutcome(StrEnum):
    """Outcome returned by Reconciler.reconcile()."""

    COMPLETED = "COMPLETED"
    CAN_RESUME = "CAN_RESUME"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class OutcomeUncertainError(AppError):
    """Raised when a write attempt's outcome is unknown and requires reconciliation."""

    def __init__(self, operation_id: str, message: str | None = None) -> None:
        super().__init__(
            ErrorCode.WRITE_UNCERTAIN,
            message or "Write outcome is uncertain; run reconciliation before retrying.",
            details={"operation_id": operation_id},
            retryable=False,
        )


class ReconciliationAmbiguousError(AppError):
    """Raised when remote state matches more than one candidate playlist."""

    def __init__(self, operation_id: str, match_count: int) -> None:
        super().__init__(
            ErrorCode.WRITE_UNCERTAIN,
            "Reconciliation found multiple matching playlists; stopping without creating.",
            details={"operation_id": operation_id, "match_count": match_count},
            retryable=False,
        )


@runtime_checkable
class ApprovedSnapshotSpec(Protocol):
    """Structural contract matching B's ApprovedSnapshot."""

    @property
    def proposal_id(self) -> str: ...

    @property
    def principal(self) -> Principal: ...

    @property
    def google_sub(self) -> str: ...

    @property
    def channel_id(self) -> str: ...

    @property
    def title(self) -> str: ...

    @property
    def description(self) -> str: ...

    @property
    def privacy(self) -> str: ...

    @property
    def video_ids(self) -> tuple[str, ...]: ...

    @property
    def digest(self) -> str: ...


@dataclass(frozen=True)
class ApprovedSnapshotCopy:
    """Immutable snapshot persisted inside an operation record for resume."""

    proposal_id: str
    principal: Principal
    google_sub: str
    channel_id: str
    title: str
    description: str
    privacy: str
    video_ids: tuple[str, ...]
    digest: str


@runtime_checkable
class ProposalTransitioner(Protocol):
    """Structural protocol matching B's ProposalRepo.transition()."""

    def transition(
        self,
        principal: Principal,
        proposal_id: str,
        *,
        expected: str,
        to: str,
        reason: str | None = None,
    ) -> object:
        """Atomically transition proposal state."""
        ...


@dataclass(frozen=True)
class OperationItemStatus:
    """Public status of a single item in an operation."""

    position: int
    video_id: str
    outcome: ItemOutcome
    external_item_id: str | None
    error_code: str | None
    attempts: int


@dataclass(frozen=True)
class OperationStatus:
    """Public status snapshot returned by OperationRepo.get_status()."""

    operation_id: str
    proposal_id: str
    state: OperationState
    target_playlist_id: str | None
    channel_id: str
    planned_units: int
    committed_units: int
    resume_count: int
    error_code: str | None
    items: tuple[OperationItemStatus, ...]
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None


@dataclass(frozen=True)
class ReconciliationResult:
    """Result of reconciling an uncertain or partial operation against YouTube state."""

    outcome: ReconciliationOutcome
    remaining_positions: tuple[int, ...]
    adopted_playlist_id: str | None = None
