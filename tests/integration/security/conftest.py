"""Offline integration setup shared by C's Phase 3 acceptance suites."""

import socket
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest

from yt_intel.config import Settings
from yt_intel.google_oauth.fake import FakeGoogleOAuth
from yt_intel.policy.ledger import ComplianceLedger
from yt_intel.security.crypto import KeyRing
from yt_intel.server.app import create_app
from yt_intel.server.auth import JwtVerifier
from yt_intel.server.grant_binding import StoredGrants
from yt_intel.server.oauth_routes import GoogleLink
from yt_intel.storage import get_engine, init_db

ORIGIN = "http://localhost:8000"


@pytest.fixture(autouse=True)
async def forbid_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("Security suites must use ASGI and fake identity providers")

    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket, "create_connection", denied)


@pytest.fixture
async def security_app(tmp_path, issuer, frozen_clock):
    config = Settings(
        _env_file=None,
        environment="test",
        data_dir=tmp_path,
        google_redirect_uri=ORIGIN + "/oauth/google/callback",
        google_client_secret="FAKE_client_secret",  # noqa: S106 -- synthetic credential
    )
    engine = get_engine(config)
    init_db(engine)
    ledger = ComplianceLedger(engine, frozen_clock)
    google = FakeGoogleOAuth(config.google_redirect_uri, frozen_clock)
    ring = KeyRing({1: b"1" * 32}, active_version=1)
    store = StoredGrants(engine)
    link = GoogleLink(
        google, ring, store, lambda event, principal: ledger.record(event, principal=principal)
    )
    verifier = JwtVerifier(issuer.issuer, "FAKE_audience", lambda: issuer.jwks)
    app = create_app(config, verifier=verifier, google_link=link)
    try:
        async with (
            httpx.AsyncClient(
                transport=httpx.ASGITransport(app), base_url=ORIGIN, follow_redirects=False
            ) as browser,
        ):
            yield SimpleNamespace(
                app=app,
                browser=browser,
                config=config,
                engine=engine,
                ledger=ledger,
                google=google,
                ring=ring,
                store=store,
                link=link,
                issuer=issuer,
                verifier=verifier,
                clock=frozen_clock,
                data_dir=tmp_path,
            )
    finally:
        engine.dispose()


@pytest.fixture
def connect_google(security_app):
    async def connect(subject="user_alpha", account="FAKE_google_alpha"):
        ctx = security_app
        start = await ctx.browser.get(
            "/oauth/google/start",
            headers={"Authorization": "Bearer " + ctx.issuer.mint(subject)},
        )
        assert start.status_code == 302
        query = parse_qs(urlsplit(start.headers["location"]).query)
        assert query["code_challenge_method"] == ["S256"]
        code = ctx.google.authorize(query["code_challenge"][0], account)
        result = await ctx.browser.get(
            "/oauth/google/callback", params={"state": query["state"][0], "code": code}
        )
        assert result.status_code == 200, result.text
        return result, query, code

    return connect
