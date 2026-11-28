import base64
import json

import httpx
import pytest

from yt_intel.common import Principal
from yt_intel.config import Settings
from yt_intel.server.app import create_app

pytestmark = pytest.mark.security


@pytest.mark.parametrize(
    "attack", ["missing", "expired", "issuer", "audience", "none", "wrong_key", "kid"]
)
async def test_untrusted_service_tokens_cannot_start_oauth(security_app, attack):
    ctx = security_app
    tokens = {
        "missing": "",
        "expired": ctx.issuer.expired(),
        "issuer": ctx.issuer.mint(iss="https://attacker.example.invalid"),
        "audience": ctx.issuer.mint(aud="FAKE_wrong_audience"),
        "none": ctx.issuer.alg_none(),
        "wrong_key": ctx.issuer.wrong_key(),
        "kid": ctx.issuer.mint(kid="FAKE_unknown_key"),
    }
    token = tokens[attack]
    headers = {"Authorization": "Bearer " + token} if token else {}
    for path in ("/oauth/google/start", "/mcp"):
        response = await ctx.browser.get(path, headers=headers)
        assert response.status_code == 401
        assert "resource_metadata" in response.headers["www-authenticate"]
        assert response.json()["request_id"] == response.headers["x-request-id"]
    assert not ctx.link.attempts
    assert ctx.verifier.verify(ctx.issuer.mint()) == Principal(ctx.issuer.issuer, "user_alpha")


async def test_origin_and_open_health(security_app, auth_headers_a):
    ctx = security_app
    health = await ctx.browser.get("/health")
    assert health.status_code == 200
    valid = await ctx.browser.get("/oauth/google/start", headers=auth_headers_a)
    assert valid.status_code == 302
    assert len(ctx.link.attempts) == 1
    for origin in ("https://attacker.example.invalid", "null", "http://localhost:8000.evil"):
        denied = await ctx.browser.get(
            "/oauth/google/start", headers=auth_headers_a | {"Origin": origin}
        )
        assert denied.status_code == 403
    assert len(ctx.link.attempts) == 1
    duplicate = await ctx.browser.get(
        "/oauth/google/start",
        headers=[
            *auth_headers_a.items(),
            ("Origin", "http://localhost:8000"),
            ("Origin", "https://attacker.example.invalid"),
        ],
    )
    assert duplicate.status_code == 403


async def test_privacy_and_deletion_guidance_are_public(security_app):
    ctx = security_app
    for path, heading in (
        ("/privacy", "Privacy policy for YouTube Video Intelligence"),
        ("/data-deletion", "Disconnecting an account and deleting data"),
    ):
        response = await ctx.browser.get(path)
        assert response.status_code == 200
        assert heading in response.text
        assert response.headers["content-type"].startswith("text/plain")
        assert response.headers["x-request-id"]


async def test_production_rejects_http_even_with_valid_bearer(security_app, tmp_path):
    ctx = security_app
    config = Settings(
        _env_file=None,
        environment="prod",
        data_dir=tmp_path / "prod",
        allowed_origins=["https://localhost:8000"],
        require_https=True,
        supabase_issuer=ctx.issuer.issuer,
        supabase_jwks_url=ctx.issuer.issuer + "/jwks",
        supabase_audience="FAKE_audience",
        google_client_id="FAKE_client_id",
        google_client_secret="FAKE_client_secret",  # noqa: S106 -- synthetic
        google_redirect_uri="https://localhost:8000/oauth/google/callback",
        token_keys=json.dumps({"1": base64.b64encode(b"1" * 32).decode()}),
    )
    app = create_app(config, verifier=ctx.verifier, google_link=ctx.link)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app)) as client:
        headers = {"Authorization": "Bearer " + ctx.issuer.mint()}
        denied = await client.get("http://localhost:8000/oauth/google/start", headers=headers)
        assert denied.status_code == 403 and not ctx.link.attempts
        health = await client.get("https://localhost:8000/health")
        assert health.status_code == 200
        allowed = await client.get("https://localhost:8000/oauth/google/start", headers=headers)
        assert allowed.status_code == 302
