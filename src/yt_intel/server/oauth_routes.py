"""Authenticated Google linking with a single-use browser continuation."""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from time import monotonic
from typing import Protocol
from urllib.parse import urlsplit

from anyio import to_thread
from fastapi import FastAPI, Request
from starlette.datastructures import State
from starlette.responses import FileResponse, JSONResponse, RedirectResponse

from yt_intel.common import AppError, ErrorCode, Principal
from yt_intel.common.errors import (
    AuthRequiredError,
    ReauthorizationRequiredError,
    TenantViolationError,
)
from yt_intel.common.oauth_util import constant_time_equals, new_pkce_pair, new_state
from yt_intel.config import Settings
from yt_intel.google_oauth.client import READ, GoogleOAuthClient
from yt_intel.security.crypto import EncryptedBlob, KeyRing, decrypt_token, encrypt_token

from .auth import resource_origin

_COOKIE = "yt_google_flow"
_CALLBACK = "/oauth/google/callback"
_DOCS = Path(__file__).resolve().parents[3] / "docs"


class GrantStorage(Protocol):
    def save(
        self, principal: Principal, sub: str, scopes: frozenset[str], blob: EncryptedBlob
    ) -> None: ...
    def get(self, principal: Principal, account_ref: str) -> tuple[str, EncryptedBlob] | None: ...
    def delete(self, principal: Principal, account_ref: str) -> None: ...


@dataclass(frozen=True)
class Attempt:
    principal: Principal
    state: str = field(repr=False)
    verifier: str = field(repr=False)
    expires: float


class GoogleLink:
    def __init__(
        self,
        google: GoogleOAuthClient,
        ring: KeyRing,
        store: GrantStorage,
        audit: Callable[[str, Principal], None],
        *,
        now: Callable[[], float] = monotonic,
    ) -> None:
        self.google = google
        self.ring = ring
        self.store = store
        self.audit = audit
        self.now = now
        self.attempts: dict[str, Attempt] = {}
        self.lock = asyncio.Lock()

    def start(self, principal: Principal) -> RedirectResponse:
        now = self.now()
        self.attempts = {k: v for k, v in self.attempts.items() if v.expires > now}
        if len(self.attempts) >= 1024:
            raise AppError(ErrorCode.RATE_LIMITED, "Too many pending authorizations")
        state, cookie = new_state(), new_state()
        verifier, challenge = new_pkce_pair()
        self.attempts[cookie] = Attempt(principal, state, verifier, now + 300)
        response = RedirectResponse(
            self.google.build_auth_url(state, challenge),
            status_code=302,
            headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"},
        )
        response.set_cookie(
            _COOKIE,
            cookie,
            max_age=300,
            path=_CALLBACK,
            httponly=True,
            secure=urlsplit(self.google.redirect_uri).scheme == "https",
            samesite="lax",
        )
        return response

    async def callback(self, request: Request) -> JSONResponse:
        if str(request.url).partition("?")[0] != self.google.redirect_uri:
            raise AppError(ErrorCode.INVALID_INPUT, "Unexpected OAuth redirect URI")
        cookie = request.cookies.get(_COOKIE, "")
        attempt = self.attempts.get(cookie)
        states = request.query_params.getlist("state")
        if (
            not attempt
            or attempt.expires <= self.now()
            or len(states) != 1
            or not constant_time_equals(attempt.state, states[0])
        ):
            raise AuthRequiredError()
        principal = getattr(request.state, "principal", None)
        if principal is not None and principal != attempt.principal:
            raise TenantViolationError()
        del self.attempts[cookie]
        codes = request.query_params.getlist("code")
        if "error" in request.query_params or len(codes) != 1 or not codes[0]:
            raise ReauthorizationRequiredError()
        principal = attempt.principal
        async with self.lock:
            tokens = await self.google.exchange_code(codes[0], attempt.verifier)
            if not tokens.refresh_token or not {"openid", READ} <= tokens.scopes:
                raise ReauthorizationRequiredError()
            sub = await self.google.subject(tokens.access_token)
            blob = encrypt_token(tokens.refresh_token, principal=principal, keyring=self.ring)
            await to_thread.run_sync(self.store.save, principal, sub, tokens.scopes, blob)
            await to_thread.run_sync(self.audit, "consent_granted", principal)
        response = JSONResponse(
            {"connected": True, "scopes": sorted(tokens.scopes)},
            headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"},
        )
        response.delete_cookie(_COOKIE, path=_CALLBACK)
        return response

    async def disconnect(self, principal: Principal, account_ref: str) -> dict[str, bool]:
        async with self.lock:
            row = await to_thread.run_sync(self.store.get, principal, account_ref)
            if not row or row[0] != account_ref:
                raise AppError(ErrorCode.NOT_FOUND_OR_UNAVAILABLE, "Account unavailable")
            revoked = False
            try:
                refresh = decrypt_token(row[1], principal=principal, keyring=self.ring)
                await self.google.revoke(refresh)
                revoked = True
            except AppError:
                pass  # The response reports unconfirmed remote revocation.
            finally:
                await to_thread.run_sync(self.store.delete, principal, account_ref)
                await to_thread.run_sync(self.audit, "consent_revoked", principal)
        return {"disconnected": True, "remote_revocation_confirmed": revoked}


def install_routes(app: FastAPI, settings: Settings) -> None:
    @app.get("/.well-known/oauth-protected-resource")
    async def metadata() -> dict[str, object]:
        return {
            "resource": resource_origin(settings) + "/mcp",
            "authorization_servers": [settings.supabase_issuer],
            "bearer_methods_supported": ["header"],
        }

    @app.get("/privacy")
    async def privacy() -> FileResponse:
        return FileResponse(
            _DOCS / "privacy_policy.md",
            media_type="text/plain",
            headers={"Link": '</data-deletion>; rel="related"'},
        )

    @app.get("/data-deletion")
    async def deletion() -> FileResponse:
        return FileResponse(_DOCS / "data_deletion.md", media_type="text/plain")

    @app.get("/oauth/google/start")
    async def start(request: Request) -> RedirectResponse:
        if request.query_params.get("write") not in (None, "false", "0"):
            raise AppError(ErrorCode.POLICY_GATE_CLOSED, "Playlist writes are unavailable")
        return get_link(request.app.state).start(request.state.principal)

    @app.get(_CALLBACK)
    async def callback(request: Request) -> JSONResponse:
        return await get_link(request.app.state).callback(request)


def get_link(state: State) -> GoogleLink:
    link = getattr(state, "google_link", None)
    if not isinstance(link, GoogleLink):
        raise AppError(ErrorCode.NOT_IMPLEMENTED, "Google linking is not configured")
    return link
