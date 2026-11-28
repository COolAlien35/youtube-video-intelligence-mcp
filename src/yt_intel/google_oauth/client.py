"""Google delegated access. Only Google OAuth/OIDC endpoints are used here."""

from dataclasses import dataclass, field
from typing import Protocol
from urllib.parse import urlencode

import httpx

from yt_intel.common import AppError, ErrorCode
from yt_intel.common.errors import ReauthorizationRequiredError

READ = "https://www.googleapis.com/auth/youtube.readonly"
WRITE = "https://www.googleapis.com/auth/youtube"
EXCHANGE_ENDPOINT = "https://oauth2.googleapis.com/token"


@dataclass(frozen=True)
class Tokens:
    access_token: str = field(repr=False)
    refresh_token: str | None = field(repr=False)
    scopes: frozenset[str]


class GoogleOAuthClient(Protocol):
    redirect_uri: str

    def build_auth_url(self, state: str, challenge: str, *, write: bool = False) -> str: ...
    async def exchange_code(self, code: str, verifier: str) -> Tokens: ...
    async def subject(self, access_token: str) -> str: ...
    async def refresh(self, refresh_token: str) -> Tokens: ...
    async def revoke(self, refresh_token: str) -> None: ...


def authorization_url(
    endpoint: str, client_id: str, redirect_uri: str, state: str, challenge: str, write: bool
) -> str:
    scopes = ["openid", READ]
    if write:
        scopes.append(WRITE)
    return (
        endpoint
        + "?"
        + urlencode(
            {
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "scope": " ".join(scopes),
                "state": state,
                "access_type": "offline",
                "include_granted_scopes": "true",
                "code_challenge_method": "S256",
                "code_challenge": challenge,
            }
        )
    )


class GoogleWebClient:
    def __init__(
        self, client_id: str, secret: str, redirect_uri: str, http: httpx.AsyncClient
    ) -> None:
        self.client_id = client_id
        self._secret = secret
        self.redirect_uri = redirect_uri
        self.http = http

    def build_auth_url(self, state: str, challenge: str, *, write: bool = False) -> str:
        return authorization_url(
            "https://accounts.google.com/o/oauth2/v2/auth",
            self.client_id,
            self.redirect_uri,
            state,
            challenge,
            write,
        )

    async def _tokens(self, fields: dict[str, str]) -> Tokens:
        try:
            r = await self.http.post(
                EXCHANGE_ENDPOINT,
                data={"client_id": self.client_id, "client_secret": self._secret, **fields},
            )
            data = r.json()
            if isinstance(data, dict) and data.get("error") == "invalid_grant":
                raise ReauthorizationRequiredError()
            r.raise_for_status()
            access = data["access_token"]
            refresh = data.get("refresh_token")
            scope = data.get("scope", "")
            if (
                not isinstance(access, str)
                or not access
                or not isinstance(scope, str)
                or (refresh is not None and not isinstance(refresh, str))
            ):
                raise ValueError("Invalid token response")
            return Tokens(access, refresh, frozenset(scope.split()))
        except (httpx.HTTPError, ValueError, KeyError, TypeError, AttributeError):
            raise AppError(
                ErrorCode.UPSTREAM_ERROR, "Google authorization service unavailable"
            ) from None

    async def exchange_code(self, code: str, verifier: str) -> Tokens:
        return await self._tokens(
            {
                "grant_type": "authorization_code",
                "code": code,
                "code_verifier": verifier,
                "redirect_uri": self.redirect_uri,
            }
        )

    async def refresh(self, refresh_token: str) -> Tokens:
        return await self._tokens({"grant_type": "refresh_token", "refresh_token": refresh_token})

    async def subject(self, access_token: str) -> str:
        try:
            r = await self.http.get(
                "https://openidconnect.googleapis.com/v1/userinfo",
                headers={"Authorization": "Bearer " + access_token},
            )
            r.raise_for_status()
            sub = r.json()["sub"]
            if not isinstance(sub, str) or not sub.strip():
                raise ValueError("Missing Google subject")
            return sub
        except (httpx.HTTPError, KeyError, TypeError, ValueError):
            raise ReauthorizationRequiredError() from None

    async def revoke(self, refresh_token: str) -> None:
        try:
            r = await self.http.post(
                "https://oauth2.googleapis.com/revoke", data={"token": refresh_token}
            )
            r.raise_for_status()
        except httpx.HTTPError:
            raise AppError(
                ErrorCode.UPSTREAM_ERROR, "Google revocation could not be confirmed"
            ) from None
