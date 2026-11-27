import secrets
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from tests.support.b_auth import FakeIssuer

from yt_intel.common import Principal
from yt_intel.config import Settings
from yt_intel.google_oauth.fake import FakeGoogleOAuth
from yt_intel.security.crypto import KeyRing, decrypt_token
from yt_intel.server.app import create_app
from yt_intel.server.oauth_routes import GoogleLink

pytestmark = [pytest.mark.unit, pytest.mark.security]
ORIGIN = "http://localhost:8000"
URI = ORIGIN + "/oauth/google/callback"


class MemoryGrants:
    def __init__(self):
        self.rows = {}

    def save(self, principal, sub, scopes, blob):
        self.rows[principal] = (sub, blob)

    def get(self, principal):
        return self.rows.get(principal)

    def delete(self, principal):
        self.rows.pop(principal, None)


@pytest.mark.parametrize("failure", [None, "principal", "state", "expiry", "redirect", "scope"])
async def test_google_binding(failure):
    issuer = FakeIssuer()
    google = FakeGoogleOAuth(URI)
    store = MemoryGrants()
    ring = KeyRing({1: secrets.token_bytes(32)}, active_version=1)
    events = []
    flow = GoogleLink(google, ring, store, lambda event, p: events.append((event, p)))
    app = create_app(
        Settings(_env_file=None, google_redirect_uri=URI),
        verifier=issuer.verifier(),
        google_link=flow,
    )
    owner = Principal("https://issuer.example", "one")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url=ORIGIN) as c:
        assert (await c.get("/privacy")).status_code == 200
        assert (await c.get("/.well-known/oauth-protected-resource")).json()[
            "resource"
        ] == ORIGIN + "/mcp"
        assert (await c.get("/oauth/google/start")).status_code == 401
        start = await c.get(
            "/oauth/google/start", headers={"Authorization": "Bearer " + issuer.mint()}
        )
        assert start.status_code == 302 and "HttpOnly" in start.headers["set-cookie"]
        q = parse_qs(urlsplit(start.headers["location"]).query)
        params = {"code": google.authorize(q["code_challenge"][0]), "state": q["state"][0]}
        headers = {}
        if failure == "principal":
            headers = {"Authorization": "Bearer " + issuer.mint("two")}
        if failure == "state":
            params["state"] = "FAKE_other"
        if failure == "expiry":
            flow.now = lambda: float("inf")
        if failure == "redirect":
            headers["Host"] = "other.invalid"
        if failure == "scope":
            google.partial_scopes = frozenset({"openid"})
        result = await c.get("/oauth/google/callback", params=params, headers=headers)
        if failure:
            assert result.status_code in {400, 401, 403} and not store.rows
            return
        assert result.status_code == 200 and events == [("consent_granted", owner)]
        assert (await c.get("/oauth/google/callback", params=params)).status_code == 401
        sub, blob = store.get(owner)
        assert decrypt_token(blob, principal=owner, keyring=ring)
        google.revoked = True
        assert await flow.disconnect(owner, sub) == {
            "disconnected": True,
            "remote_revocation_confirmed": False,
        }
        assert not store.rows and events[-1] == ("consent_revoked", owner)
