"""Unit tests for TokenSource."""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

import pytest

from yt_intel.common.errors import AppError, ErrorCode
from yt_intel.common.types import Principal
from yt_intel.config.settings import Settings
from yt_intel.security import (
    EncryptedBlob,
    KeyRing,
    OAuthRefreshResult,
    ReauthorizationRequiredError,
    TokenSource,
    decrypt_token,
    encrypt_token,
)
from yt_intel.storage import GrantRepo, ScopedSession, get_engine, init_db, session_scope

if TYPE_CHECKING:
    from pathlib import Path

    from sqlalchemy import Engine

_READONLY_SCOPE = "https://www.googleapis.com/auth/youtube.readonly"


class _FakeOAuthClient:
    def __init__(
        self,
        *,
        access_token: str = "ya29.ephemeral-access",  # noqa: S107
        rotated_refresh: str | None = None,
        raise_invalid_grant: bool = False,
    ) -> None:
        self._access = access_token
        self._rotated = rotated_refresh
        self._raise_invalid_grant = raise_invalid_grant
        self.calls = 0

    def refresh_access_token(self, refresh_token: str) -> OAuthRefreshResult:
        self.calls += 1
        if self._raise_invalid_grant:
            raise AppError(
                ErrorCode.AUTH_EXPIRED_OR_REVOKED,
                "Token revoked",
                details={"reason": "invalid_grant"},
            )
        return OAuthRefreshResult(access_token=self._access, refresh_token=self._rotated)


def _make_engine(tmp_path: Path) -> Engine:
    settings = Settings(_env_file=None, data_dir=tmp_path / "data")
    engine = get_engine(settings)
    init_db(engine)
    return engine


def _make_keyring() -> KeyRing:
    return KeyRing({1: os.urandom(32)}, active_version=1)


def test_token_source_not_connected_and_insufficient_scope(tmp_path: Path) -> None:
    principal = Principal(issuer="https://issuer.example", subject="alice")
    engine = _make_engine(tmp_path)
    keyring = _make_keyring()
    oauth = _FakeOAuthClient()

    with session_scope(engine) as session:
        repo = GrantRepo(ScopedSession(session, principal))
        source = TokenSource(repo, keyring, oauth)

        with pytest.raises(ReauthorizationRequiredError) as exc:
            source.access_token(principal)
        assert exc.value.reason == "not_connected"
        assert exc.value.code is ErrorCode.AUTH_REQUIRED

        blob = encrypt_token("1//refresh-initial", principal=principal, keyring=keyring)
        repo.save(principal, "acct-1", "openid", blob)

        with pytest.raises(ReauthorizationRequiredError) as exc2:
            source.access_token(principal, required_scopes=(_READONLY_SCOPE,))
        assert exc2.value.reason == "insufficient_scope"
        assert exc2.value.code is ErrorCode.FORBIDDEN
        assert oauth.calls == 0


def test_token_source_refresh_success_rotation_and_no_leak(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    principal = Principal(issuer="https://issuer.example", subject="alice")
    engine = _make_engine(tmp_path)
    keyring = _make_keyring()

    secret_access = "ya29.secret-ephemeral-access-token"  # noqa: S105
    oauth = _FakeOAuthClient(
        access_token=secret_access,
        rotated_refresh="1//refresh-rotated-new",
    )

    with session_scope(engine) as session:
        repo = GrantRepo(ScopedSession(session, principal))
        initial_blob = encrypt_token("1//refresh-initial", principal=principal, keyring=keyring)
        repo.save(principal, "acct-1", _READONLY_SCOPE, initial_blob)
        source = TokenSource(repo, keyring, oauth)

        with caplog.at_level(logging.INFO):
            token = source.access_token(principal, required_scopes=(_READONLY_SCOPE,))

        assert token == secret_access
        assert secret_access not in caplog.text
        assert "1//refresh-rotated-new" not in caplog.text

        updated = repo.get(principal)
        assert updated is not None
        decrypted = decrypt_token(
            EncryptedBlob(
                key_version=updated.key_version,
                nonce=updated.nonce,
                ciphertext=updated.ciphertext,
            ),
            principal=principal,
            keyring=keyring,
        )
        assert decrypted == "1//refresh-rotated-new"


def test_token_source_invalid_grant(tmp_path: Path) -> None:
    principal = Principal(issuer="https://issuer.example", subject="alice")
    engine = _make_engine(tmp_path)
    keyring = _make_keyring()

    with session_scope(engine) as session:
        repo = GrantRepo(ScopedSession(session, principal))
        blob = encrypt_token("1//refresh-revoked", principal=principal, keyring=keyring)
        repo.save(principal, "acct-1", _READONLY_SCOPE, blob)

        oauth = _FakeOAuthClient(raise_invalid_grant=True)
        source = TokenSource(repo, keyring, oauth)

        with pytest.raises(ReauthorizationRequiredError) as exc:
            source.access_token(principal, required_scopes=(_READONLY_SCOPE,))
        assert exc.value.reason == "invalid_grant"
        assert exc.value.code is ErrorCode.AUTH_EXPIRED_OR_REVOKED
