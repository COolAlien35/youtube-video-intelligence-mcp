import json
import secrets
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import httpx
import httpx2
import jsonschema
from mcp.client import ClientSession
from mcp.client.streamable_http import streamable_http_client
from sqlalchemy import select, text
from tests.support.b_auth import FakeIssuer

from yt_intel.config import Settings
from yt_intel.google_oauth.fake import FakeGoogleOAuth
from yt_intel.policy.ledger import ComplianceLedger
from yt_intel.security.crypto import KeyRing
from yt_intel.server.app import create_app
from yt_intel.server.grant_binding import StoredGrants
from yt_intel.server.oauth_routes import GoogleLink
from yt_intel.storage import get_engine, init_db, session_scope
from yt_intel.storage.models import CacheEntryRecord


async def test_account_metrics_schema_isolation_and_disconnect(tmp_path):
    origin = "http://localhost:8000"
    uri = origin + "/oauth/google/callback"
    settings = Settings(
        _env_file=None,
        data_dir=tmp_path,
        google_redirect_uri=uri,
        max_workflow_starts_per_minute=30,
    )
    engine = get_engine(settings)
    init_db(engine)
    google = FakeGoogleOAuth(uri)
    ledger = ComplianceLedger(engine)
    link = GoogleLink(
        google,
        KeyRing({1: secrets.token_bytes(32)}, active_version=1),
        StoredGrants(engine),
        lambda event, p: ledger.record(event, principal=p),
    )
    issuer = FakeIssuer()
    app = create_app(settings, verifier=issuer.verifier(), google_link=link)

    async def call(user, name, args):
        async with (
            httpx2.AsyncClient(
                transport=httpx2.ASGITransport(app),
                base_url=origin,
                headers={"Authorization": "Bearer " + issuer.mint(user)},
            ) as client,
            streamable_http_client(origin + "/mcp", http_client=client) as streams,
            ClientSession(*streams) as session,
        ):
            await session.initialize()
            result = await session.call_tool(name, args)
            if name == "engagement_analysis":
                tool = next(t for t in (await session.list_tools()).tools if t.name == name)
                for kind, schema in (("input", tool.input_schema), ("output", tool.output_schema)):
                    path = (
                        Path(__file__).resolve().parents[2]
                        / "docs/tools"
                        / f"engagement_analysis.{kind}.schema.json"
                    )
                    assert json.loads(path.read_text()) == schema
                jsonschema.validate(result.structured_content, tool.output_schema)
                assert "principal" not in tool.input_schema["properties"]
                assert '"liked_at"' not in json.dumps(result.structured_content)
            return result.structured_content

    try:
        async with (
            app.router.lifespan_context(app),
            httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url=origin) as browser,
        ):
            assert (await browser.post("/mcp")).status_code == 401
            args = {
                "source": "liked_videos",
                "period": {"start": "2026-01-01", "end": "2027-01-01"},
            }
            assert (await call("alpha", "engagement_analysis", args))["error"]["details"][
                "reason"
            ] == "not_connected"
            for user in ("alpha", "beta"):
                start = await browser.get(
                    "/oauth/google/start", headers={"Authorization": "Bearer " + issuer.mint(user)}
                )
                q = parse_qs(urlsplit(start.headers["location"]).query)
                code = google.authorize(q["code_challenge"][0], "user_" + user)
                assert (
                    await browser.get(
                        "/oauth/google/callback", params={"code": code, "state": q["state"][0]}
                    )
                ).status_code == 200
            for invalid in (
                {"start": "bad", "end": "2027-01-01"},
                {"start": "2026-01-01", "end": "2026-01-01"},
            ):
                assert (await call("alpha", "engagement_analysis", args | {"period": invalid}))[
                    "error"
                ]["code"] == "INVALID_INPUT"
            a = await call("alpha", "engagement_analysis", args)
            b = await call("beta", "engagement_analysis", args)
            assert a["data"]["metrics"]["channels"] != b["data"]["metrics"]["channels"]
            assert (await call("alpha", "engagement_analysis", args))["data"]["coverage"][
                "from_cache"
            ]
            playlist = args | {"source": "playlist_items", "playlist_id": "PLSYN_user_alpha_0"}
            assert (await call("alpha", "engagement_analysis", playlist))["data"]["enrichment"][
                "available"
            ] > 0
            assert (await call("alpha", "disconnect_google", {"account_ref": "user_alpha"}))["ok"]
            assert (await call("alpha", "engagement_analysis", args))["error"][
                "code"
            ] == "AUTH_EXPIRED_OR_REVOKED"
            assert (await call("beta", "engagement_analysis", args))["data"]["coverage"][
                "from_cache"
            ]
            with session_scope(engine) as db:
                assert dict(
                    db.execute(
                        text("SELECT event, COUNT(*) FROM policy_events GROUP BY event")
                    ).all()
                ) == {"consent_granted": 2, "consent_revoked": 1}
                owners = set(db.scalars(select(CacheEntryRecord.principal_key)))
                assert owners == {issuer.verifier().verify(issuer.mint("beta")).key}
    finally:
        engine.dispose()
