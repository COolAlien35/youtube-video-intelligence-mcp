"""In-memory Google OAuth access-token source backed by GrantRepo and AES-256-GCM."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, Protocol

from yt_intel.common.errors import AppError, ErrorCode
from yt_intel.security.crypto import EncryptedBlob, KeyRing, decrypt_token, encrypt_token

if TYPE_CHECKING:
    from collections.abc import Sequence

    from yt_intel.common.types import Principal
    from yt_intel.storage.grants import GrantRepo

logger = logging.getLogger(__name__)

_DEFAULT_READONLY_SCOPES: tuple[str, ...] = ("https://www.googleapis.com/auth/youtube.readonly",)

ReauthReason = Literal["not_connected", "insufficient_scope", "invalid_grant"]

_REASON_ERROR_CODE: dict[ReauthReason, ErrorCode] = {
    "not_connected": ErrorCode.AUTH_REQUIRED,
    "insufficient_scope": ErrorCode.FORBIDDEN,
    "invalid_grant": ErrorCode.AUTH_EXPIRED_OR_REVOKED,
}

_REASON_MESSAGE: dict[ReauthReason, str] = {
    "not_connected": "Google account is not connected",
    "insufficient_scope": "Connected Google grant lacks required scopes",
    "invalid_grant": "Google authorization expired or was revoked",
}


class ReauthorizationRequiredError(AppError):
    """Structured error raised when a principal must (re-)authorize Google access."""

    def __init__(self, reason: ReauthReason, message: str | None = None) -> None:
        self.reason: ReauthReason = reason
        super().__init__(
            _REASON_ERROR_CODE[reason],
            message or _REASON_MESSAGE[reason],
            details={"reason": reason},
        )


@dataclass(frozen=True)
class OAuthRefreshResult:
    """Result returned by an OAuth refresh call (never persisted with access token)."""

    access_token: str
    refresh_token: str | None = None

    def __repr__(self) -> str:
        return "OAuthRefreshResult(access_token='<redacted>', refresh_token_rotated=...)"


class OAuthTokenRefresher(Protocol):
    """Protocol matching GoogleOAuthClient's refresh method."""

    def refresh_access_token(self, refresh_token: str) -> OAuthRefreshResult:
        """Exchange *refresh_token* for a short-lived access token (and optional new refresh)."""
        ...


class TokenSource:
    """Decrypts principal-bound refresh tokens, refreshes in memory, and saves rotations."""

    def __init__(
        self,
        grant_repo: GrantRepo,
        keyring: KeyRing,
        oauth_client: OAuthTokenRefresher,
    ) -> None:
        self._grants = grant_repo
        self._keyring = keyring
        self._oauth = oauth_client

    def access_token(
        self,
        principal: Principal,
        *,
        required_scopes: Sequence[str] = _DEFAULT_READONLY_SCOPES,
    ) -> str:
        """Return a fresh in-memory access token for *principal* or raise re-auth error."""
        grant = self._grants.get(principal)
        if grant is None or grant.status != "active":
            raise ReauthorizationRequiredError("not_connected")

        granted = set(grant.granted_scopes.split())
        if not set(required_scopes).issubset(granted):
            raise ReauthorizationRequiredError("insufficient_scope")

        if grant.ciphertext is None or grant.nonce is None or grant.key_version is None:
            raise ReauthorizationRequiredError("not_connected")

        blob = EncryptedBlob(
            key_version=grant.key_version,
            nonce=grant.nonce,
            ciphertext=grant.ciphertext,
        )
        refresh_plaintext = decrypt_token(blob, principal=principal, keyring=self._keyring)

        try:
            refreshed = self._oauth.refresh_access_token(refresh_plaintext)
        except ReauthorizationRequiredError:
            raise
        except AppError as exc:
            if exc.code is ErrorCode.AUTH_EXPIRED_OR_REVOKED or (
                exc.details.get("reason") == "invalid_grant"
            ):
                raise ReauthorizationRequiredError("invalid_grant") from exc
            raise

        if refreshed.refresh_token and refreshed.refresh_token != refresh_plaintext:
            rotated_blob = encrypt_token(
                refreshed.refresh_token,
                principal=principal,
                keyring=self._keyring,
            )
            self._grants.save(
                principal,
                grant.account_ref,
                grant.granted_scopes,
                rotated_blob,
                status=grant.status,
            )
            logger.info(
                "google_refresh_token_rotated",
                extra={"key_version": rotated_blob.key_version},
            )

        return refreshed.access_token
