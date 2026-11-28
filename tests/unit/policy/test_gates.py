from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine

from yt_intel.common.errors import AppError, ErrorCode, PolicyGateClosedError
from yt_intel.policy.gates import Capability, GateId, PolicyGates
from yt_intel.policy.ledger import ComplianceLedger
from yt_intel.provider.factory import build_provider

pytestmark = [pytest.mark.unit, pytest.mark.security]


def make(**flags):
    return PolicyGates.from_settings(
        SimpleNamespace(**flags), ComplianceLedger(create_engine("sqlite://"))
    )


def test_all_default_closed():
    gates = make()
    for gate in GateId:
        with pytest.raises(PolicyGateClosedError):
            gates.require(gate)
    with gates.ledger.engine.connect() as c:
        assert (
            c.exec_driver_sql(
                "SELECT COUNT(*) FROM policy_events WHERE event='gate_denied'"
            ).scalar()
            == 8
        )


@pytest.mark.parametrize(
    "flag,evidence", [(True, None), ("true", "POL-123"), (True, "  "), (True, "../../secret")]
)
def test_invalid_open(flag, evidence):
    assert not make(pol_08_open=flag, pol_08_evidence=evidence).is_open(GateId.POL_08)


def test_capability_requires_all_evidence():
    gates = make(pol_08_open=True, pol_08_evidence="POL-808")
    assert not gates.live_youtube_allowed(Capability.ACCOUNT)
    for n in [4, 5, 7]:
        setattr(gates.settings, f"pol_{n:02d}_open", True)
        setattr(gates.settings, f"pol_{n:02d}_evidence", "docs/policy/clearance.md")
    assert gates.live_youtube_allowed(Capability.ACCOUNT)
    assert not gates.live_youtube_allowed(Capability.ACCOUNT, Capability.DERIVED)
    assert not gates.live_youtube_allowed()


def test_factory_fail_closed_and_fixture_unaudited():
    gates = make()
    conf = SimpleNamespace(live_youtube_enabled=True, fixtures_dir=None)
    with pytest.raises(PolicyGateClosedError):
        build_provider(conf, gates=gates)
    conf.live_youtube_enabled = False
    assert build_provider(conf, gates=gates).__class__.__name__ == "FixtureProvider"
    with gates.ledger.engine.connect() as c:
        assert c.exec_driver_sql("select count(*) from policy_events").scalar() == 1


def test_no_live_adapter_even_after_clearance():
    gates = make()
    for g in GateId:
        setattr(gates.settings, g.name.lower() + "_open", True)
        setattr(gates.settings, g.name.lower() + "_evidence", "POL-101")
    assert gates.live_youtube_allowed()
    with pytest.raises(AppError) as exc:
        build_provider(SimpleNamespace(live_youtube_enabled=True), gates=gates)
    assert exc.value.code == ErrorCode.NOT_IMPLEMENTED


def test_playlist_write_capability_requires_gates_and_setting():
    gates = make()
    assert not gates.playlist_write_allowed()
    for n in [4, 5, 7, 8]:
        setattr(gates.settings, f"pol_{n:02d}_open", True)
        setattr(gates.settings, f"pol_{n:02d}_evidence", "docs/policy/write_gating.md")
    # Gates alone are insufficient while playlist_writes_enabled defaults closed.
    assert gates.live_youtube_allowed(Capability.PLAYLIST_WRITE)
    assert not gates.playlist_write_allowed()
    gates.settings.playlist_writes_enabled = True
    assert gates.playlist_write_allowed()
