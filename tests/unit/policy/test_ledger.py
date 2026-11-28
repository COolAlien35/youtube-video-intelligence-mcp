from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError

from yt_intel.common import FakeClock, Principal
from yt_intel.policy.ledger import ComplianceLedger, GateId

pytestmark = [pytest.mark.unit, pytest.mark.security]


def test_ledger_and_unlink():
    engine = create_engine("sqlite://")
    ledger = ComplianceLedger(engine, FakeClock(datetime(2026, 11, 27, tzinfo=UTC)))
    p = Principal("synthetic", "one")
    for event in ["consent_granted", "consent_revoked", "deletion_requested"]:
        ledger.record(event, principal=p)
    ComplianceLedger(engine)
    with engine.connect() as c:
        rows = c.exec_driver_sql("SELECT * FROM policy_events").fetchall()
        assert len(rows) == 3 and len({r.subject_ref for r in rows}) == 1
        assert p.key not in str(rows) and rows[0].recorded_at.endswith("Z")
    ledger.forget_principal(p)
    with engine.connect() as c:
        assert not c.exec_driver_sql("SELECT * FROM policy_subject_links").fetchall()
        assert c.exec_driver_sql("SELECT count(*) FROM policy_events").scalar() == 3
    for sql in [
        "DELETE FROM policy_events",
        "UPDATE policy_events SET event='other'",
        "INSERT OR REPLACE INTO policy_events SELECT * FROM policy_events WHERE event_id=1",
    ]:
        with pytest.raises(IntegrityError), engine.begin() as c:
            c.exec_driver_sql(sql)


def test_safe_metadata():
    ledger = ComplianceLedger(create_engine("sqlite://"))
    for detail in ["Authorization: Bearer FAKE_private", "https://invalid/?code=FAKE", None]:
        with pytest.raises(ValueError):
            ledger.record("gate_opened", gate=GateId.POL_01, detail=detail)
    with pytest.raises(ValueError):
        ledger.record("consent_granted")
    with ledger.engine.connect() as c:
        assert c.exec_driver_sql("SELECT count(*) FROM policy_events").scalar() == 0
