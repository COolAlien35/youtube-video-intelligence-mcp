"""Unit tests for GrantRepo principal-bound encrypted grant storage."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from yt_intel.common.errors import AppError, ErrorCode
from yt_intel.common.types import Principal
from yt_intel.config import Settings
from yt_intel.security import KeyRing, decrypt_token, encrypt_token
from yt_intel.storage import GrantRepo, ScopedSession, get_engine, init_db, session_scope

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.unit


def _keyring() -> KeyRing:
    return KeyRing({1: bytes([0x11]) * 32, 2: bytes([0x22]) * 32}, active_version=1)


def test_grant_repo_save_get_update_delete_and_isolation(tmp_path: Path) -> None:
    """GrantRepo saves encrypted grants bound to one principal and isolates tenants."""
    engine = get_engine(Settings(_env_file=None, data_dir=tmp_path / "grants"))
    init_db(engine)
    p_a = Principal(issuer="https://issuer.example", subject="alice")
    p_b = Principal(issuer="https://issuer.example", subject="bob")
    ring = _keyring()

    blob_1 = encrypt_token("refresh-a-1", principal=p_a, keyring=ring)
    with session_scope(engine) as session:
        repo_a = GrantRepo(ScopedSession(session, p_a))
        saved = repo_a.save(
            p_a,
            account_ref="google-sub-1",
            scopes=["https://www.googleapis.com/auth/youtube.readonly"],
            blob=blob_1,
        )
        assert saved.principal_key == p_a.key
        assert saved.key_version == 1

    # Bob cannot read Alice's grant or use Alice's repo
    with session_scope(engine) as session:
        repo_b = GrantRepo(ScopedSession(session, p_b))
        assert repo_b.get(p_b) is None
        with pytest.raises(AppError) as exc_info:
            repo_b.get(p_a)
        assert exc_info.value.code is ErrorCode.FORBIDDEN

    # Update Alice's grant under key version 2 and decrypt
    ring_v2 = KeyRing({1: bytes([0x11]) * 32, 2: bytes([0x22]) * 32}, active_version=2)
    blob_2 = encrypt_token("refresh-a-2", principal=p_a, keyring=ring_v2)
    with session_scope(engine) as session:
        repo_a = GrantRepo(ScopedSession(session, p_a))
        repo_a.save(
            p_a,
            account_ref="google-sub-1",
            scopes="https://www.googleapis.com/auth/youtube.readonly",
            blob=blob_2,
        )
        fetched = repo_a.get(p_a, account_ref="google-sub-1")
        assert fetched is not None
        assert fetched.key_version == 2
        assert fetched.nonce is not None
        assert fetched.ciphertext is not None

        from yt_intel.security import EncryptedBlob

        recovered = decrypt_token(
            EncryptedBlob(
                key_version=fetched.key_version,
                nonce=fetched.nonce,
                ciphertext=fetched.ciphertext,
            ),
            principal=p_a,
            keyring=ring_v2,
        )
        assert recovered == "refresh-a-2"

        deleted = repo_a.delete(p_a, account_ref="google-sub-1")
        assert deleted == 1
        assert repo_a.get(p_a) is None
