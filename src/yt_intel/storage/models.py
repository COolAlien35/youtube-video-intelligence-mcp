"""SQLAlchemy 2.x ORM models matching docs/architecture/data_model.md."""

from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base, UTCDateTime


def _utc_now() -> datetime:
    return datetime.now(UTC)


class PrincipalRecord(Base):
    """Verified issuer/subject pair (tenant root)."""

    __tablename__ = "principals"

    principal_key: Mapped[str] = mapped_column(String(255), primary_key=True)
    issuer: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=_utc_now)


class GoogleGrantRecord(Base):
    """Encrypted Google OAuth grant bound to a principal and linked account (Phase 3+)."""

    __tablename__ = "google_grants"
    __table_args__ = (UniqueConstraint("principal_key", "account_ref", name="uq_grant_account"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    principal_key: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("principals.principal_key", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    account_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    ciphertext: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    nonce: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    key_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    granted_scopes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=_utc_now)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=_utc_now)


class DailyQuotaRecord(Base):
    """Shared daily quota ledger across all principals (Pacific midnight reset)."""

    __tablename__ = "daily_quotas"

    quota_day: Mapped[date] = mapped_column(Date, primary_key=True)
    common_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    common_reserved: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    search_calls_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    search_calls_reserved: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=_utc_now)


class QuotaReservationRecord(Base):
    """Atomic per-workflow quota reservation against a daily quota row."""

    __tablename__ = "quota_reservations"

    reservation_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    quota_day: Mapped[date] = mapped_column(
        Date,
        ForeignKey("daily_quotas.quota_day", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    principal_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    workflow_id: Mapped[str] = mapped_column(String(128), nullable=False)
    common_reserved: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    search_reserved: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    common_settled: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    search_settled: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="reserved")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=_utc_now)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=_utc_now)


class WorkflowLimitRecord(Base):
    """Per-principal active workflow count and rolling start-rate tracking (ADR-09)."""

    __tablename__ = "workflow_limits"
    __table_args__ = (UniqueConstraint("principal_key", "workflow_id", name="uq_wf_limit"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    principal_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    workflow_id: Mapped[str] = mapped_column(String(128), nullable=False)
    started_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=_utc_now)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class CacheEntryRecord(Base):
    """Tenant-scoped cache entry for metadata, private signals, and derived results."""

    __tablename__ = "cache_entries"
    __table_args__ = (
        UniqueConstraint(
            "principal_key",
            "category",
            "canonical_resource_id",
            "account_ref",
            name="uq_cache_key",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    principal_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    canonical_resource_id: Mapped[str] = mapped_column(String(255), nullable=False)
    account_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False)


class ProposalRecord(Base):
    """Immutable playlist creation/modification proposal with single-use approval."""

    __tablename__ = "proposals"

    proposal_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    principal_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    account_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    target_channel: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    visibility: Mapped[str] = mapped_column(String(32), nullable=False, default="private")
    constraints_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    digest: Mapped[str] = mapped_column(String(128), nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    approval_ref: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=_utc_now)


class ProposalItemRecord(Base):
    """Ordered video item belonging to a proposal."""

    __tablename__ = "proposal_items"
    __table_args__ = (
        UniqueConstraint("proposal_id", "position", name="uq_proposal_item_pos"),
        UniqueConstraint("proposal_id", "canonical_video_id", name="uq_proposal_item_video"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    principal_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    proposal_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("proposals.proposal_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    canonical_video_id: Mapped[str] = mapped_column(String(32), nullable=False)
    runtime_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    language: Mapped[str | None] = mapped_column(String(32), nullable=True)


class OperationRecord(Base):
    """External playlist write operation tracked separately from local approval."""

    __tablename__ = "operations"

    operation_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    principal_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    proposal_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("proposals.proposal_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    target_playlist_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="creating")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=_utc_now)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=_utc_now)


class OperationItemRecord(Base):
    """Per-item external write outcome for reconciliation."""

    __tablename__ = "operation_items"
    __table_args__ = (UniqueConstraint("operation_id", "position", name="uq_operation_item_pos"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    principal_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    operation_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("operations.operation_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    video_id: Mapped[str] = mapped_column(String(32), nullable=False)
    external_item_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    outcome: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")


class DeletionRequestRecord(Base):
    """Tracks personal-data purge requests across stores (7-day deadline)."""

    __tablename__ = "deletion_requests"

    request_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    principal_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    requested_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=_utc_now)
    deadline: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    progress: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)


class PolicyComplianceRecord(Base):
    """Policy gate determinations (platform-wide or principal-consent-specific)."""

    __tablename__ = "policy_compliance_ledger"

    evidence_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    gate_id: Mapped[str] = mapped_column(String(32), nullable=False)
    scope: Mapped[str] = mapped_column(String(32), nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    evidence_ref: Mapped[str] = mapped_column(Text, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=_utc_now)
    principal_key: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
