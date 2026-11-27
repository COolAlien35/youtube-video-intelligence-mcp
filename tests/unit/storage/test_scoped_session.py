"""Unit tests for ScopedSession tenant isolation."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

import pytest

from yt_intel.common.errors import AppError, ErrorCode
from yt_intel.common.types import Principal
from yt_intel.config import Settings
from yt_intel.storage import (
    DailyQuotaRecord,
    PrincipalRecord,
    QuotaReservationRecord,
    ScopedSession,
    get_engine,
    init_db,
    session_scope,
)

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.unit


def test_scoped_session_requires_principal(tmp_path: Path) -> None:
    """ScopedSession rejects missing or invalid Principal objects."""
    engine = get_engine(Settings(_env_file=None, data_dir=tmp_path / "s1"))
    init_db(engine)
    with session_scope(engine) as session, pytest.raises(AppError) as exc_info:
        ScopedSession(session, None)  # type: ignore[arg-type]
    assert exc_info.value.code is ErrorCode.FORBIDDEN


def test_scoped_session_filters_queries_and_allows_shared_daily_quota(tmp_path: Path) -> None:
    """Queries on principal-owned tables filter automatically; DailyQuotaRecord stays shared."""
    engine = get_engine(Settings(_env_file=None, data_dir=tmp_path / "s2"))
    init_db(engine)
    p_a = Principal(issuer="https://issuer.example", subject="alice")
    p_b = Principal(issuer="https://issuer.example", subject="bob")

    with session_scope(engine) as session:
        session.add(DailyQuotaRecord(quota_day=date(2026, 11, 27)))
        session.add(
            QuotaReservationRecord(
                reservation_id="res-a",
                quota_day=date(2026, 11, 27),
                principal_key=p_a.key,
                workflow_id="wf-a",
            )
        )
        session.add(
            QuotaReservationRecord(
                reservation_id="res-b",
                quota_day=date(2026, 11, 27),
                principal_key=p_b.key,
                workflow_id="wf-b",
            )
        )

    with session_scope(engine) as session:
        scoped_a = ScopedSession(session, p_a)
        rows = scoped_a.scalars(scoped_a.select(QuotaReservationRecord))
        assert [r.reservation_id for r in rows] == ["res-a"]

        shared_quota = scoped_a.scalars(scoped_a.select(DailyQuotaRecord))
        assert len(shared_quota) == 1


def test_scoped_session_rejects_cross_tenant_write_and_delete(tmp_path: Path) -> None:
    """ScopedSession rejects staging or deleting records owned by another principal."""
    engine = get_engine(Settings(_env_file=None, data_dir=tmp_path / "s3"))
    init_db(engine)
    p_a = Principal(issuer="https://issuer.example", subject="alice")
    p_b = Principal(issuer="https://issuer.example", subject="bob")

    with session_scope(engine) as session:
        scoped_a = ScopedSession(session, p_a)
        foreign = PrincipalRecord(
            principal_key=p_b.key,
            issuer=p_b.issuer,
            subject=p_b.subject,
        )
        with pytest.raises(AppError) as exc_info:
            scoped_a.add(foreign)
        assert exc_info.value.code is ErrorCode.FORBIDDEN

        with pytest.raises(AppError) as del_exc:
            scoped_a.delete(foreign)
        assert del_exc.value.code is ErrorCode.FORBIDDEN
