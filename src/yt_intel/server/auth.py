"""Validate service tokens using only keys obtained from the configured issuer."""

from collections.abc import Callable
from contextvars import ContextVar
from threading import Lock
from time import monotonic
from typing import Any
from urllib.parse import urlsplit

import httpx
import jwt
from anyio import to_thread
from starlette.datastructures import Headers
from starlette.types import ASGIApp, Receive, Scope, Send

from yt_intel.common import AppError, ErrorCode, Principal
from yt_intel.common.errors import AuthRequiredError, InvalidTokenError
from yt_intel.config import Settings

from .errors import error_response

principal_var: ContextVar[Principal | None] = ContextVar("verified_principal", default=None)
_ALGS = ("ES256", "RS256")


class JwtVerifier:
    def __init__(
        self, issuer: str, audience: str, fetch: Callable[[], dict[str, Any]], *, ttl: float = 600
    ) -> None:
        self.issuer = issuer
        self.audience = audience
        self.fetch = fetch
        self.ttl = ttl
        self._keys: dict[str, jwt.PyJWK] = {}
        self._expires = 0.0
        self._next_refresh = 0.0
        self._lock = Lock()

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "JwtVerifier":
        from yt_intel.config import get_settings

        settings = settings or get_settings()
        url = settings.supabase_jwks_url

        def fetch() -> dict[str, Any]:
            if not url:
                raise InvalidTokenError()
            response = httpx.get(url, timeout=5, follow_redirects=False)
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict):
                raise InvalidTokenError()
            return data

        return cls(settings.supabase_issuer, settings.supabase_audience, fetch)

    def _key(self, kid: str) -> jwt.PyJWK:
        with self._lock:
            now = monotonic()
            if now < self._expires and kid in self._keys:
                return self._keys[kid]
            if now >= self._next_refresh:
                self._next_refresh = now + 30
                keys = jwt.PyJWKSet.from_dict(self.fetch()).keys
                self._keys = {
                    key.key_id: key
                    for key in keys
                    if key.key_id
                    and key.public_key_use in (None, "sig")
                    and key.algorithm_name in _ALGS
                }
                self._expires = now + self.ttl
            if kid not in self._keys or now >= self._expires:
                raise InvalidTokenError()
            return self._keys[kid]

    def verify(self, token: str) -> Principal:
        if not self.issuer or not self.audience:
            raise InvalidTokenError()
        try:
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")
            if header.get("alg") not in _ALGS or not isinstance(kid, str) or not kid:
                raise InvalidTokenError()
            key = self._key(kid)
            if header["alg"] != key.algorithm_name:
                raise InvalidTokenError()
            claims = jwt.decode(
                token,
                key,
                algorithms=[key.algorithm_name],
                issuer=self.issuer,
                audience=self.audience,
                options={"require": ["iss", "aud", "exp", "sub"]},
            )
            return Principal(self.issuer, claims["sub"])
        except (jwt.PyJWTError, httpx.HTTPError, ValueError, TypeError, KeyError, OverflowError):
            raise InvalidTokenError() from None


def resource_origin(config: Settings) -> str:
    parsed = urlsplit(config.google_redirect_uri)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}"
    return f"http://{config.host}:{config.port}"


class AuthMiddleware:
    def __init__(self, app: ASGIApp, verifier: JwtVerifier, config: Settings) -> None:
        self.app = app
        self.verifier = verifier
        self.require_https = config.require_https or config.environment == "prod"
        self.metadata = resource_origin(config) + "/.well-known/oauth-protected-resource"

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        if self.require_https and scope["scheme"] != "https":
            await error_response(AppError(ErrorCode.FORBIDDEN, "HTTPS required"))(
                scope, receive, send
            )
            return
        if scope["path"] in {
            "/health",
            "/privacy",
            "/data-deletion",
            "/.well-known/oauth-protected-resource",
        }:
            await self.app(scope, receive, send)
            return
        values = Headers(scope=scope).getlist("authorization")
        if scope["path"] == "/oauth/google/callback" and not values:
            # Browser redirect authenticates via the single-use bound state and cookie.
            await self.app(scope, receive, send)
            return
        try:
            if len(values) != 1:
                raise AuthRequiredError()
            scheme, _, token = values[0].partition(" ")
            if scheme.lower() != "bearer" or not token:
                raise AuthRequiredError()
            principal = await to_thread.run_sync(self.verifier.verify, token)
        except AppError as exc:
            response = error_response(exc)
            response.headers["WWW-Authenticate"] = f'Bearer resource_metadata="{self.metadata}"'
            await response(scope, receive, send)
            return
        scope.setdefault("state", {})["principal"] = principal
        binding = principal_var.set(principal)
        try:
            await self.app(scope, receive, send)
        finally:
            principal_var.reset(binding)
