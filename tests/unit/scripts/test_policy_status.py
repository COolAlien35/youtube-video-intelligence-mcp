"""Tests for scripts/policy_status.py."""

from types import SimpleNamespace

import pytest

from scripts.policy_status import render_gate_status
from yt_intel.policy.ledger import GateId

pytestmark = [pytest.mark.unit, pytest.mark.security]


def test_all_gates_listed_and_closed_by_default() -> None:
    md = render_gate_status(SimpleNamespace())
    for gate in GateId:
        assert f"`{gate.value}`" in md
    assert "`open`" not in md
    assert md.count("`closed`") == len(GateId)


def test_evidence_reference_shown_only_when_configured_and_open() -> None:
    settings = SimpleNamespace(
        pol_04_open=True,
        pol_04_evidence="docs/policy/write_gating.md",
        pol_08_open=False,
        pol_08_evidence="POL-999",
    )
    md = render_gate_status(settings)
    assert "docs/policy/write_gating.md" in md
    assert "POL-999" not in md
