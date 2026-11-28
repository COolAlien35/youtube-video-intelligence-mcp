"""Unit tests for yt_intel.storage models, WAL pragmas, FKs, UTC, and principal scoping."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from yt_intel.config import Settings
from yt_intel.storage import (
    Base,
    CacheEntryRecord,
    GoogleGrantRecord,
    PrincipalRecord,
    get_engine,
    init_db,
    scoped_select,
    session_scope,
)

if TYPE_CHECKING:
    from pathlib import Path


def _make_settings(tmp_path: Path) -> Settings:
    data_dir = tmp_path / "data"
    return Settings(_env_file=None, data_dir=data_dir)


@pytest.mark.unit
def test_get_engine_creates_data_dir_and_enables_wal_and_fk(tmp_path: Path) -> None:
    """get_engine creates data_dir, enables WAL mode and foreign_keys=ON."""
    settings = _make_settings(tmp_path)
    assert not settings.data_dir.exists()

    engine = get_engine(settings)
    init_db(engine)

    assert settings.data_dir.exists()
    with engine.connect() as conn:
        journal_mode = conn.execute(text("PRAGMA journal_mode")).scalar_one()
        foreign_keys = conn.execute(text("PRAGMA foreign_keys")).scalar_one()
    assert str(journal_mode).lower() == "wal"
    assert foreign_keys == 1


@pytest.mark.unit
def test_foreign_key_enforcement_rejects_orphan_grant(tmp_path: Path) -> None:
    """Inserting a GoogleGrantRecord for a missing principal must fail FK constraint."""
    engine = get_engine(_make_settings(tmp_path))
    init_db(engine)

    with pytest.raises(IntegrityError), session_scope(engine) as session:
        session.add(
            GoogleGrantRecord(
                principal_key="missing|user",
                account_ref="acct-1",
                status="active",
            )
        )


@pytest.mark.unit
def test_every_principal_key_column_is_indexed(tmp_path: Path) -> None:
    """Every table with a principal_key column must have an index on principal_key."""
    engine = get_engine(_make_settings(tmp_path))
    init_db(engine)
    inspector = inspect(engine)

    for table_name, table in Base.metadata.tables.items():
        if "principal_key" not in table.c:
            continue
        col = table.c["principal_key"]
        if col.primary_key:
            continue
        indexes = inspector.get_indexes(table_name)
        indexed_cols = {col_name for idx in indexes for col_name in idx["column_names"]}
        assert "principal_key" in indexed_cols, f"{table_name}.principal_key is missing an index"


@pytest.mark.unit
def test_utc_datetime_round_trip(tmp_path: Path) -> None:
    """Timestamps are stored in UTC and returned as timezone-aware UTC datetimes."""
    engine = get_engine(_make_settings(tmp_path))
    init_db(engine)

    ist = timezone(timedelta(hours=5, minutes=30))
    local_time = datetime(2026, 11, 26, 12, 0, 0, tzinfo=ist)

    with session_scope(engine) as session:
        session.add(
            PrincipalRecord(
                principal_key="iss|u1",
                issuer="iss",
                subject="u1",
                created_at=local_time,
            )
        )

    with session_scope(engine) as session:
        row = session.get(PrincipalRecord, "iss|u1")
        assert row is not None
        assert row.created_at.tzinfo == UTC
        assert row.created_at == local_time.astimezone(UTC)


@pytest.mark.unit
@pytest.mark.security
@pytest.mark.parametrize("bad_key", ["", "   ", "\t\n"])
def test_scoped_select_rejects_empty_principal_key(bad_key: str) -> None:
    """scoped_select must refuse empty or blank principal_key values."""
    with pytest.raises(ValueError, match="principal_key"):
        scoped_select(CacheEntryRecord, bad_key)


@pytest.mark.unit
@pytest.mark.security
def test_scoped_select_isolates_principals(tmp_path: Path) -> None:
    """scoped_select returns only rows belonging to the requested principal."""
    engine = get_engine(_make_settings(tmp_path))
    init_db(engine)
    now = datetime.now(UTC)

    with session_scope(engine) as session:
        session.add_all(
            [
                CacheEntryRecord(
                    principal_key="iss|alice",
                    category="video",
                    canonical_resource_id="vid1",
                    fetched_at=now,
                    expires_at=now + timedelta(hours=1),
                    payload='{"owner": "alice"}',
                ),
                CacheEntryRecord(
                    principal_key="iss|bob",
                    category="video",
                    canonical_resource_id="vid1",
                    fetched_at=now,
                    expires_at=now + timedelta(hours=1),
                    payload='{"owner": "bob"}',
                ),
            ]
        )

    with session_scope(engine) as session:
        alice_rows = session.scalars(scoped_select(CacheEntryRecord, "iss|alice")).all()
        assert len(alice_rows) == 1
        assert alice_rows[0].principal_key == "iss|alice"
        assert "alice" in alice_rows[0].payload
