"""Server-side policy decisions, independent of the live provider enable switch."""

from dataclasses import dataclass
from enum import StrEnum

from yt_intel.common import Principal
from yt_intel.common.errors import PolicyGateClosedError
from yt_intel.config import Settings, get_settings
from yt_intel.storage import get_engine

from .ledger import ComplianceLedger, Event, GateId, evidence_reference


class Capability(StrEnum):
    DERIVED = "derived"
    ACCOUNT = "account"
    CROSS_OWNER = "cross_owner"
    PRESENTATION = "presentation"
    PLAYLIST_WRITE = "playlist_write"


_REQUIRED = {
    Capability.DERIVED: (GateId.POL_01, GateId.POL_02, GateId.POL_03),
    Capability.ACCOUNT: (GateId.POL_04, GateId.POL_05),
    Capability.CROSS_OWNER: (GateId.POL_06,),
    Capability.PRESENTATION: (GateId.POL_07,),
    Capability.PLAYLIST_WRITE: (GateId.POL_04, GateId.POL_05),
}


@dataclass(frozen=True)
class PolicyGates:
    settings: object
    ledger: ComplianceLedger

    @classmethod
    def from_settings(
        cls, settings: object | None = None, ledger: ComplianceLedger | None = None
    ) -> "PolicyGates":
        config = settings if settings is not None else get_settings()
        if ledger is None:
            storage_config = config if isinstance(config, Settings) else get_settings()
            ledger = ComplianceLedger(get_engine(storage_config))
        return cls(config, ledger)

    def is_open(self, gate: GateId, *, principal: Principal | None = None) -> bool:
        gate = GateId(gate)
        prefix = gate.name.lower()
        enabled = getattr(self.settings, f"{prefix}_open", False) is True
        evidence = evidence_reference(getattr(self.settings, f"{prefix}_evidence", None))
        opened = enabled and evidence is not None
        self.ledger.record(
            Event.GATE_OPENED if opened else Event.GATE_DENIED,
            gate,
            principal,
            evidence if opened else None,
        )
        return opened

    def require(self, *gates: GateId, principal: Principal | None = None) -> None:
        for gate in gates or tuple(GateId):
            if not self.is_open(gate, principal=principal):
                raise PolicyGateClosedError()

    def live_youtube_allowed(
        self, *capabilities: Capability, principal: Principal | None = None
    ) -> bool:
        # With no declared capability the factory must satisfy every gate.
        required = {GateId.POL_08, GateId.POL_07}
        for capability in capabilities or tuple(Capability):
            required.update(_REQUIRED[Capability(capability)])
        return all(self.is_open(g, principal=principal) for g in sorted(required))

    def playlist_write_allowed(self, *, principal: Principal | None = None) -> bool:
        """Return True only when write policy gates and PLAYLIST_WRITES_ENABLED are both open."""
        if getattr(self.settings, "playlist_writes_enabled", False) is not True:
            return False
        return self.live_youtube_allowed(Capability.PLAYLIST_WRITE, principal=principal)
