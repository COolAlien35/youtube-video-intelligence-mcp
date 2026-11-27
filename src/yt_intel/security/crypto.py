"""Key-versioned AES-256-GCM token encryption bound to Principal AAD."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from yt_intel.common.errors import AppError, ErrorCode
from yt_intel.config.settings import parse_token_keys

if TYPE_CHECKING:
    from yt_intel.common.types import Principal
    from yt_intel.config.settings import Settings

_AES_256_KEY_BYTES = 32
_GCM_NONCE_BYTES = 12


@dataclass(frozen=True)
class EncryptedBlob:
    """Versioned AES-256-GCM ciphertext bundle."""

    key_version: int
    nonce: bytes
    ciphertext: bytes

    def __repr__(self) -> str:
        """Never expose raw nonce or ciphertext bytes in logs or tracebacks."""
        return (
            f"EncryptedBlob(key_version={self.key_version}, "
            f"nonce_len={len(self.nonce)}, ciphertext_len={len(self.ciphertext)})"
        )


class KeyRing:
    """In-memory ring of 32-byte AES-256 keys indexed by positive integer version."""

    def __init__(self, keys: dict[int, bytes], *, active_version: int) -> None:
        if not keys:
            raise ValueError("KeyRing requires at least one key")
        for version, key in keys.items():
            if version <= 0:
                raise ValueError("Key version must be a positive integer")
            if len(key) != _AES_256_KEY_BYTES:
                raise ValueError(f"Key version {version} must be exactly 32 bytes")
        if active_version not in keys:
            raise ValueError("active_version must exist in KeyRing")
        self._keys = dict(keys)
        self.active_version = active_version

    @classmethod
    def from_settings(cls, settings: Settings) -> KeyRing:
        """Construct a KeyRing from Settings.token_keys and active_token_key_version."""
        parsed = parse_token_keys(settings.token_keys.get_secret_value())
        return cls(parsed, active_version=settings.active_token_key_version)

    def get_key(self, version: int) -> bytes:
        """Return the 32-byte key for *version* or raise AppError."""
        key = self._keys.get(version)
        if key is None:
            raise AppError(
                ErrorCode.INTERNAL_ERROR,
                "Requested token key version is unavailable",
                details={"key_version": version},
            )
        return key


def _principal_aad(principal: Principal) -> bytes:
    return principal.key.encode("utf-8")


def encrypt_token(
    plaintext: str,
    *,
    principal: Principal,
    keyring: KeyRing,
) -> EncryptedBlob:
    """Encrypt *plaintext* with the active AES-256-GCM key and principal AAD."""
    if not plaintext:
        raise ValueError("Cannot encrypt an empty token")

    key_version = keyring.active_version
    key = keyring.get_key(key_version)
    nonce = os.urandom(_GCM_NONCE_BYTES)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext.encode("utf-8"), _principal_aad(principal))
    return EncryptedBlob(key_version=key_version, nonce=nonce, ciphertext=ciphertext)


def decrypt_token(
    blob: EncryptedBlob,
    *,
    principal: Principal,
    keyring: KeyRing,
) -> str:
    """Decrypt *blob* using its recorded key_version and verify principal AAD."""
    if len(blob.nonce) != _GCM_NONCE_BYTES or not blob.ciphertext:
        raise AppError(
            ErrorCode.AUTH_EXPIRED_OR_REVOKED,
            "Stored token payload is malformed",
        )

    key = keyring.get_key(blob.key_version)
    try:
        plaintext_bytes = AESGCM(key).decrypt(
            blob.nonce, blob.ciphertext, _principal_aad(principal)
        )
    except InvalidTag as exc:
        raise AppError(
            ErrorCode.AUTH_EXPIRED_OR_REVOKED,
            "Stored token failed integrity verification",
        ) from exc
    return plaintext_bytes.decode("utf-8")


def rotate_blob(
    blob: EncryptedBlob,
    *,
    principal: Principal,
    keyring: KeyRing,
) -> EncryptedBlob:
    """Re-encrypt *blob* under ``keyring.active_version``."""
    plaintext = decrypt_token(blob, principal=principal, keyring=keyring)
    return encrypt_token(plaintext, principal=principal, keyring=keyring)
