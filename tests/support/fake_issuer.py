"""Synthetic RS256 issuer for security tests.

Each instance owns an ephemeral RSA key and exposes only its public JWK set.
It never contacts an identity provider and must not be used with real tokens.
"""

from __future__ import annotations

import base64
import hashlib
import json
import time
from typing import Any

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _json(value: dict[str, Any]) -> str:
    return _b64(json.dumps(value, separators=(",", ":"), sort_keys=True).encode())


class FakeIssuer:
    """Mint JWT-shaped test tokens and publish a JWKS-compatible public key."""

    def __init__(
        self,
        *,
        issuer: str = "https://fake-issuer.example.invalid",
        kid: str = "FAKE_kid_1",
        algorithm: str = "RS256",
    ) -> None:
        self.issuer = issuer
        self.kid = kid
        self.algorithm = algorithm
        self._key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    @property
    def jwks(self) -> dict[str, list[dict[str, str]]]:
        public = self._key.public_key().public_numbers()
        return {
            "keys": [
                {
                    "kty": "RSA",
                    "use": "sig",
                    "alg": "RS256",
                    "kid": self.kid,
                    "n": _b64(public.n.to_bytes((public.n.bit_length() + 7) // 8, "big")),
                    "e": _b64(public.e.to_bytes((public.e.bit_length() + 7) // 8, "big")),
                }
            ]
        }

    def mint(
        self,
        sub: str = "user_alpha",
        *,
        iss: str | None = None,
        aud: str = "FAKE_audience",
        exp_delta: int = 3600,
        kid: str | None = None,
        algorithm: str | None = None,
        **claims: Any,
    ) -> str:
        header = {"alg": algorithm or self.algorithm, "kid": kid or self.kid, "typ": "JWT"}
        payload: dict[str, Any] = {
            "iss": self.issuer if iss is None else iss,
            "sub": sub,
            "aud": aud,
            "iat": int(time.time()),
            "exp": int(time.time()) + exp_delta,
        }
        payload.update(claims)
        signing_input = f"{_json(header)}.{_json(payload)}".encode()
        if header["alg"] == "none":
            signature = b""
        elif header["alg"] == "RS256":
            signature = self._key.sign(
                signing_input,
                padding.PKCS1v15(),
                hashes.SHA256(),
            )
        else:
            raise ValueError(f"Unsupported fake algorithm {header['alg']}")
        return signing_input.decode() + "." + _b64(signature)

    def wrong_key(self, sub: str = "user_alpha", **kwargs: Any) -> str:
        other = FakeIssuer(issuer=self.issuer, kid=self.kid)
        return other.mint(sub, **kwargs)

    def alg_none(self, sub: str = "user_alpha", **kwargs: Any) -> str:
        return self.mint(sub, algorithm="none", **kwargs)

    def expired(self, sub: str = "user_alpha", **kwargs: Any) -> str:
        return self.mint(sub, exp_delta=-1, **kwargs)

    def private_key_pem(self) -> bytes:
        """Expose the key only for tests that need to inspect key rotation."""
        return self._key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )

    @property
    def key_fingerprint(self) -> str:
        public_der = self._key.public_key().public_bytes(
            serialization.Encoding.DER,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        return hashlib.sha256(public_der).hexdigest()
