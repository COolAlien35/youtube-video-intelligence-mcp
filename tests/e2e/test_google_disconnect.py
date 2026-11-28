import secrets
from urllib.parse import parse_qs, urlsplit

import httpx
import httpx2
import pytest
from mcp.client import ClientSession
from mcp.client.streamable_http import streamable_http_client
from tests.support.b_auth import FakeIssuer

from yt_intel.common import Principal
from yt_intel.config import Settings
from yt_intel.google_oauth.fake import FakeGoogleOAuth
from yt_intel.security.crypto import KeyRing
from yt_intel.server.app import create_app
from yt_intel.server.grant_binding import StoredGrants
from yt_intel.server.oauth_routes import GoogleLink
from yt_intel.storage import get_engine, init_db

pytestmark = [pytest.mark.e2e, pytest.mark.security]


async def test_disconnect_selects_only_verified_principals_named_account(tmp_path):
    origin = "http://localhost:8000"
    uri = origin + "/oauth/google/callback"
    config = Settings(_env_file=None, data_dir=tmp_path, google_redirect_uri=uri)
    issuer = FakeIssuer()
    google = FakeGoogleOAuth(uri)
    engine = get_engine(config)
    init_db(engine)
    store = StoredGrants(engine)
    ring = KeyRing({1: secrets.token_bytes(32)}, active_version=1)
    events = []
    link = GoogleLink(google, ring, store, lambda event, p: events.append((event, p)))
    app = create_app(config, verifier=issuer.verifier(), google_link=link)

    async def disconnect(subject, account):
        async with (
            httpx2.AsyncClient(
                transport=httpx2.ASGITransport(app=app),
                base_url=origin,
                headers={"Authorization": "Bearer " + issuer.mint(subject)},
            ) as http,
            streamable_http_client(origin + "/mcp", http_client=http) as streams,
            ClientSession(*streams) as session,
        ):
            await session.initialize()
            result = await session.call_tool("disconnect_google", {"account_ref": account})
            return result.structured_content

    try:
        async with (
            app.router.lifespan_context(app),
            httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url=origin) as browser,
        ):
            for subject, account in [("one", "first"), ("one", "second"), ("two", "second")]:
                start = await browser.get(
                    "/oauth/google/start",
                    headers={"Authorization": "Bearer " + issuer.mint(subject)},
                )
                query = parse_qs(urlsplit(start.headers["location"]).query)
                code = google.authorize(query["code_challenge"][0], account)
                result = await browser.get(
                    "/oauth/google/callback", params={"state": query["state"][0], "code": code}
                )
                assert result.status_code == 200
            denied = await disconnect("two", "first")
            assert denied["error"]["code"] == "NOT_FOUND_OR_UNAVAILABLE"
            success = await disconnect("one", "second")
            assert success["data"] == {"disconnected": True, "remote_revocation_confirmed": True}
            owner = Principal("https://issuer.example", "one")
            other = Principal("https://issuer.example", "two")
            assert store.get(owner, "second") is None
            assert store.get(owner, "first") and store.get(other, "second")
            assert events[-1] == ("consent_revoked", owner)
    finally:
        engine.dispose()
