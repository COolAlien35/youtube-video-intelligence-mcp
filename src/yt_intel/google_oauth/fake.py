"""Offline Google authorization double with one-use codes and expiring grants."""

import base64
import hashlib
from datetime import datetime, timedelta

from yt_intel.common import Clock, SystemClock
from yt_intel.common.errors import ReauthorizationRequiredError
from yt_intel.common.oauth_util import constant_time_equals, new_state

from .client import READ, Tokens, authorization_url


class FakeGoogleOAuth:
    def __init__(self, redirect_uri: str, clock: Clock | None = None) -> None:
        self.redirect_uri = redirect_uri
        self.clock = clock or SystemClock()
        self.expired = False
        self.revoked = False
        self.partial_scopes: frozenset[str] | None = None
        self._codes: dict[str, tuple[str, str, frozenset[str]]] = {}
        self._grants: dict[str, tuple[str, datetime, frozenset[str]]] = {}
        self._subjects: dict[str, str] = {}

    def build_auth_url(self, state: str, challenge: str, *, write: bool = False) -> str:
        return authorization_url(
            "https://google.invalid/authorize",
            "synthetic",
            self.redirect_uri,
            state,
            challenge,
            write,
        )

    def authorize(
        self,
        challenge: str,
        sub: str = "synthetic-google",
        scopes: frozenset[str] = frozenset({"openid", READ}),
    ) -> str:
        code = new_state()
        self._codes[code] = (challenge, sub, scopes)
        return code

    async def exchange_code(self, code: str, verifier: str) -> Tokens:
        receipt = self._codes.pop(code, None)
        challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest())
            .rstrip(b"=")
            .decode()
        )
        if (
            not receipt
            or self.expired
            or self.revoked
            or not constant_time_equals(receipt[0], challenge)
        ):
            raise ReauthorizationRequiredError()
        _, sub, scopes = receipt
        if self.partial_scopes is not None:
            scopes = self.partial_scopes
        access, refresh = new_state(), new_state()
        self._subjects[access] = sub
        self._grants[refresh] = (sub, self.clock.now(), scopes)
        return Tokens(access, refresh, scopes)

    async def subject(self, access_token: str) -> str:
        if access_token not in self._subjects:
            raise ReauthorizationRequiredError()
        return self._subjects[access_token]

    async def refresh(self, refresh_token: str) -> Tokens:
        grant = self._grants.get(refresh_token)
        if (
            not grant
            or self.revoked
            or self.expired
            or self.clock.now() >= grant[1] + timedelta(days=7)
        ):
            raise ReauthorizationRequiredError()
        access = new_state()
        self._subjects[access] = grant[0]
        return Tokens(access, None, grant[2])

    async def revoke(self, refresh_token: str) -> None:
        if self.revoked or self._grants.pop(refresh_token, None) is None:
            raise ReauthorizationRequiredError()
