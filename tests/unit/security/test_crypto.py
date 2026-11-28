"""Unit tests for key-versioned AES-256-GCM token encryption."""

from __future__ import annotations

import base64
import json

import pytest
from pydantic import SecretStr

from yt_intel.common.errors import AppError, ErrorCode
from yt_intel.common.types import Principal
from yt_intel.config import Settings
from yt_intel.security import (
    EncryptedBlob,
    KeyRing,
    decrypt_token,
    encrypt_token,
    rotate_blob,
)

pytestmark = pytest.mark.unit


def _make_key(byte_val: int) -> bytes:
    return bytes([byte_val]) * 32


def _make_keyring(*, active_version: int = 1) -> KeyRing:
    return KeyRing({1: _make_key(0x11), 2: _make_key(0x22)}, active_version=active_version)


def test_encrypt_decrypt_round_trip_and_plaintext_absent() -> None:
    """EncryptedBlob round-trips cleanly and never contains plaintext bytes."""
    principal = Principal(issuer="https://issuer.example", subject="user-1")
    keyring = _make_keyring(active_version=1)
    plaintext = "fake-refresh-value-12345"

    blob = encrypt_token(plaintext, principal=principal, keyring=keyring)

    assert blob.key_version == 1
    assert len(blob.nonce) == 12
    assert plaintext.encode("utf-8") not in blob.ciphertext
    assert plaintext not in repr(blob)
    assert decrypt_token(blob, principal=principal, keyring=keyring) == plaintext


def test_encrypt_uses_fresh_nonce_per_call() -> None:
    """Encrypting the same token twice produces distinct 12-byte nonces."""
    principal = Principal(issuer="https://issuer.example", subject="user-1")
    keyring = _make_keyring()

    blob1 = encrypt_token("same-token", principal=principal, keyring=keyring)
    blob2 = encrypt_token("same-token", principal=principal, keyring=keyring)

    assert blob1.nonce != blob2.nonce
    assert blob1.ciphertext != blob2.ciphertext


def test_wrong_principal_aad_fails_decryption() -> None:
    """Ciphertext copied to another principal fails AES-GCM AAD verification."""
    principal_a = Principal(issuer="https://issuer.example", subject="user-a")
    principal_b = Principal(issuer="https://issuer.example", subject="user-b")
    keyring = _make_keyring()

    blob = encrypt_token("tenant-a-secret", principal=principal_a, keyring=keyring)

    with pytest.raises(AppError) as exc_info:
        decrypt_token(blob, principal=principal_b, keyring=keyring)
    assert exc_info.value.code is ErrorCode.AUTH_EXPIRED_OR_REVOKED


def test_tampered_ciphertext_fails_decryption() -> None:
    """Bit-flipping ciphertext fails GCM authentication tag verification."""
    principal = Principal(issuer="https://issuer.example", subject="user-1")
    keyring = _make_keyring()

    blob = encrypt_token("refresh-secret", principal=principal, keyring=keyring)
    tampered = EncryptedBlob(
        key_version=blob.key_version,
        nonce=blob.nonce,
        ciphertext=bytes([blob.ciphertext[0] ^ 0xFF]) + blob.ciphertext[1:],
    )

    with pytest.raises(AppError) as exc_info:
        decrypt_token(tampered, principal=principal, keyring=keyring)
    assert exc_info.value.code is ErrorCode.AUTH_EXPIRED_OR_REVOKED


def test_keyring_rejects_wrong_key_size_and_missing_active_version() -> None:
    """KeyRing strictly enforces 32-byte keys and active_version membership."""
    with pytest.raises(ValueError, match="32 bytes"):
        KeyRing({1: b"too-short"}, active_version=1)

    with pytest.raises(ValueError, match="active_version"):
        KeyRing({1: _make_key(0x11)}, active_version=2)


def test_rotate_blob_reencrypts_under_active_version() -> None:
    """rotate_blob decrypts with old version and encrypts under active_version."""
    principal = Principal(issuer="https://issuer.example", subject="user-1")
    keyring_v1 = _make_keyring(active_version=1)
    blob_v1 = encrypt_token("rotate-me", principal=principal, keyring=keyring_v1)
    assert blob_v1.key_version == 1

    keyring_v2 = _make_keyring(active_version=2)
    blob_v2 = rotate_blob(blob_v1, principal=principal, keyring=keyring_v2)

    assert blob_v2.key_version == 2
    assert blob_v2.nonce != blob_v1.nonce
    assert decrypt_token(blob_v2, principal=principal, keyring=keyring_v2) == "rotate-me"


def test_keyring_from_settings() -> None:
    """KeyRing.from_settings parses Settings.token_keys and active_token_key_version."""
    key_b64 = base64.b64encode(_make_key(0x33)).decode("ascii")
    settings = Settings(
        _env_file=None,
        token_keys=SecretStr(json.dumps({"3": key_b64})),
        active_token_key_version=3,
    )
    keyring = KeyRing.from_settings(settings)
    principal = Principal(issuer="https://issuer.example", subject="user-1")

    blob = encrypt_token("from-settings", principal=principal, keyring=keyring)
    assert blob.key_version == 3
    assert decrypt_token(blob, principal=principal, keyring=keyring) == "from-settings"
