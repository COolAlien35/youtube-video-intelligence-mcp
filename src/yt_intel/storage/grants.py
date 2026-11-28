"""Repository for principal-bound encrypted Google OAuth grants."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from yt_intel.common.errors import AppError, ErrorCode
from yt_intel.storage.models import GoogleGrantRecord, PrincipalRecord

if TYPE_CHECKING:
    from collections.abc import Iterable

    from yt_intel.common.types import Principal
    from yt_intel.security.crypto import EncryptedBlob
    from yt_intel.storage.scoped import ScopedSession


def _normalize_scopes(scopes: str | Iterable[str]) -> str:
    if isinstance(scopes, str):
        parts = [part.strip() for part in scopes.split() if part.strip()]
    else:
        parts = [part.strip() for part in scopes if part.strip()]
    return " ".join(dict.fromkeys(parts))


class GrantRepo:
    """Persist and retrieve encrypted Google OAuth grants scoped to a Principal."""

    def __init__(self, scoped_session: ScopedSession) -> None:
        self._scoped = scoped_session

    def _assert_principal(self, principal: Principal) -> None:
        if principal.key != self._scoped.principal.key:
            raise AppError(
                ErrorCode.FORBIDDEN,
                "Principal does not match ScopedSession tenant",
            )

    def _ensure_principal_record(self, principal: Principal) -> None:
        stmt = self._scoped.select(PrincipalRecord)
        existing = self._scoped.scalar_one_or_none(stmt)
        if existing is None:
            self._scoped.add(
                PrincipalRecord(
                    principal_key=principal.key,
                    issuer=principal.issuer,
                    subject=principal.subject,
                )
            )
            self._scoped.flush()

    def save(
        self,
        principal: Principal,
        account_ref: str,
        scopes: str | Iterable[str],
        blob: EncryptedBlob,
        *,
        status: str = "active",
    ) -> GoogleGrantRecord:
        """Upsert an encrypted Google grant bound to *principal* and *account_ref*."""
        self._assert_principal(principal)
        if not account_ref.strip():
            raise AppError(ErrorCode.INVALID_INPUT, "account_ref must not be empty")

        self._ensure_principal_record(principal)
        normalized_scopes = _normalize_scopes(scopes)
        now = datetime.now(UTC)

        existing = self.get(principal, account_ref=account_ref)
        if existing is not None:
            existing.ciphertext = blob.ciphertext
            existing.nonce = blob.nonce
            existing.key_version = blob.key_version
            existing.granted_scopes = normalized_scopes
            existing.status = status
            existing.updated_at = now
            self._scoped.flush()
            return existing

        record = GoogleGrantRecord(
            principal_key=principal.key,
            account_ref=account_ref,
            ciphertext=blob.ciphertext,
            nonce=blob.nonce,
            key_version=blob.key_version,
            granted_scopes=normalized_scopes,
            status=status,
            created_at=now,
            updated_at=now,
        )
        self._scoped.add(record)
        self._scoped.flush()
        return record

    def get(
        self,
        principal: Principal,
        *,
        account_ref: str | None = None,
    ) -> GoogleGrantRecord | None:
        """Fetch a grant for *principal*, optionally filtered by *account_ref*."""
        self._assert_principal(principal)
        stmt = self._scoped.select(GoogleGrantRecord)
        if account_ref is not None:
            stmt = stmt.where(GoogleGrantRecord.account_ref == account_ref)
        else:
            stmt = stmt.order_by(GoogleGrantRecord.updated_at.desc())
        records = self._scoped.scalars(stmt)
        return records[0] if records else None

    def delete(
        self,
        principal: Principal,
        *,
        account_ref: str | None = None,
    ) -> int:
        """Delete grants for *principal* (or a single *account_ref*) and return count."""
        self._assert_principal(principal)
        stmt = self._scoped.select(GoogleGrantRecord)
        if account_ref is not None:
            stmt = stmt.where(GoogleGrantRecord.account_ref == account_ref)
        records = self._scoped.scalars(stmt)
        for record in records:
            self._scoped.delete(record)
        self._scoped.flush()
        return len(records)
