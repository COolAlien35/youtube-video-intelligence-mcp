"""Principal type — §0.4 interface contract (stub for D's implementation)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Principal:
    """Verified issuer/subject pair (tenant root)."""

    issuer: str
    subject: str

    @property
    def key(self) -> str:
        """Return the principal_key stored in every tenant-scoped column."""
        return f"{self.issuer}|{self.subject}"
