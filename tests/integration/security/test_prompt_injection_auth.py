import httpx2
import pytest
from mcp.client import ClientSession
from mcp.client.streamable_http import streamable_http_client

from yt_intel.common.errors import PolicyGateClosedError
from yt_intel.policy.gates import GateId, PolicyGates
from yt_intel.provider.factory import build_provider

pytestmark = pytest.mark.security


async def test_metadata_instructions_cannot_authorize_oauth_or_playlist_writes(
    security_app, fixture_provider, principal_a, monkeypatch
):
    ctx = security_app
    metadata = (await fixture_provider.get_videos(["SYNV_000007"])).videos[0]
    assert "approval" in metadata.title and "confirmation" in metadata.description
    writes = []

    async def forbidden(*args, **kwargs):
        writes.append((args, kwargs))
        raise AssertionError("Metadata must not cause an OAuth or provider write")

    for method in ("create_playlist", "insert_playlist_item"):
        monkeypatch.setattr(fixture_provider, method, forbidden)
    monkeypatch.setattr(ctx.google, "exchange_code", forbidden)
    monkeypatch.setattr(ctx.google, "build_auth_url", lambda *a, **k: writes.append("oauth"))
    rejected = await ctx.browser.get(
        "/oauth/google/start", headers={"Authorization": "Bearer " + metadata.description}
    )
    assert rejected.status_code == 401
    async with (
        ctx.app.router.lifespan_context(ctx.app),
        httpx2.AsyncClient(
            transport=httpx2.ASGITransport(ctx.app),
            base_url="http://localhost:8000",
            headers={"Authorization": "Bearer " + ctx.issuer.mint()},
        ) as client,
        streamable_http_client("http://localhost:8000/mcp", http_client=client) as streams,
        ClientSession(*streams) as session,
    ):
        await session.initialize()
        for topic in (metadata.title, metadata.description):
            result = await session.call_tool(
                "propose_playlist", {"topic": topic, "max_total_seconds": 7200}
            )
            assert result.structured_content["error"]["code"] == "NOT_IMPLEMENTED"
        denied = await session.call_tool(
            "confirm_execute_playlist", {"proposal_id": metadata.title}
        )
        assert denied.structured_content["error"]["code"] == "NOT_IMPLEMENTED"
    assert not writes and not ctx.link.attempts
    assert ctx.store.get(principal_a, "FAKE_google_alpha") is None
    assert ctx.verifier.verify(ctx.issuer.mint()) == principal_a


def test_closed_live_selection_records_denial_without_provider_creation(security_app):
    ctx = security_app
    gates = PolicyGates.from_settings(ctx.config, ctx.ledger)
    assert all(not gates.is_open(gate) for gate in GateId)
    settings = ctx.config.model_copy(update={"live_youtube_enabled": True})
    with pytest.raises(PolicyGateClosedError):
        build_provider(settings, gates=gates)
    with ctx.engine.connect() as connection:
        events = connection.exec_driver_sql("SELECT event FROM policy_events").scalars().all()
        assert len(events) >= 9 and set(events) == {"gate_denied"}
