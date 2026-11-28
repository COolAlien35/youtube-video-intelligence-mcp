"""Append-only decision journal with erasable principal associations."""

import re
from enum import StrEnum
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.engine import Engine

from yt_intel.common import Clock, Principal, SystemClock
from yt_intel.common.timeutil import format_utc

from .migration import migrate


class GateId(StrEnum):
    POL_01 = "POL-01"
    POL_02 = "POL-02"
    POL_03 = "POL-03"
    POL_04 = "POL-04"
    POL_05 = "POL-05"
    POL_06 = "POL-06"
    POL_07 = "POL-07"
    POL_08 = "POL-08"


class Event(StrEnum):
    GATE_DENIED = "gate_denied"
    GATE_OPENED = "gate_opened"
    CONSENT_GRANTED = "consent_granted"
    CONSENT_REVOKED = "consent_revoked"
    DELETION_REQUESTED = "deletion_requested"


def evidence_reference(value: object) -> str | None:
    """Accept a numbered evidence record or repository-relative Markdown path."""
    if isinstance(value, str) and re.fullmatch(
        r"(?:[A-Z]{1,12}-[0-9]{1,12}|docs/(?:[A-Za-z0-9_-]+/)*[A-Za-z0-9_-]+\.md)", value
    ):
        return value
    return None


class ComplianceLedger:
    def __init__(self, engine: Engine, clock: Clock | None = None) -> None:
        self.engine = engine
        self.clock = clock or SystemClock()
        migrate(engine)

    def record(
        self,
        event: Event | str,
        gate: GateId | None = None,
        principal: Principal | None = None,
        detail: str | None = None,
    ) -> None:
        kind = Event(event)
        gate_event = kind in {Event.GATE_DENIED, Event.GATE_OPENED}
        if gate_event != (gate is not None):
            raise ValueError("Gate decisions require a gate")
        if not gate_event and principal is None:
            raise ValueError("Account events require a verified principal")
        if detail is not None and evidence_reference(detail) is None:
            raise ValueError("Only an evidence reference can be recorded")
        if kind == Event.GATE_OPENED and detail is None:
            raise ValueError("An open decision requires written evidence")
        with self.engine.begin() as conn:
            ref = None
            if principal is not None:
                conn.execute(
                    text("""INSERT INTO policy_subject_links VALUES (:key,:ref)
                    ON CONFLICT(principal_key) DO NOTHING"""),
                    {"key": principal.key, "ref": uuid4().hex},
                )
                ref = conn.execute(
                    text("""SELECT subject_ref FROM policy_subject_links
                                     WHERE principal_key=:key"""),
                    {"key": principal.key},
                ).scalar_one()
            conn.execute(
                text("""INSERT INTO policy_events
                (recorded_at,event,gate,subject_ref,evidence_ref)
                VALUES (:now,:event,:gate,:ref,:evidence)"""),
                {
                    "now": format_utc(self.clock.now()),
                    "event": kind.value,
                    "gate": GateId(gate).value if gate else None,
                    "ref": ref,
                    "evidence": detail,
                },
            )

    def forget_principal(self, principal: Principal) -> None:
        """Call during the account purge to unlink all historical journal entries."""
        with self.engine.begin() as conn:
            conn.execute(
                text("DELETE FROM policy_subject_links WHERE principal_key=:key"),
                {"key": principal.key},
            )
