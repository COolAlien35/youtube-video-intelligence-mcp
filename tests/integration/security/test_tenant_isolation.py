import httpx2
import pytest
from mcp.client import ClientSession
from mcp.client.streamable_http import streamable_http_client
from sqlalchemy import select

from yt_intel.cache.store import CacheStore
from yt_intel.common import AppError, Principal
from yt_intel.security.crypto import decrypt_token
from yt_intel.server.app import create_app
from yt_intel.storage import session_scope
from yt_intel.storage.grants import GrantRepo
from yt_intel.storage.models import GoogleGrantRecord
from yt_intel.storage.scoped import ScopedSession

pytestmark = pytest.mark.security


async def disconnect(ctx, subject, account):
    app = create_app(ctx.config, verifier=ctx.verifier, google_link=ctx.link)
    async with (
        app.router.lifespan_context(app),
        httpx2.AsyncClient(
            transport=httpx2.ASGITransport(app),
            base_url="http://localhost:8000",
            headers={"Authorization": "Bearer " + ctx.issuer.mint(subject)},
        ) as client,
        streamable_http_client("http://localhost:8000/mcp", http_client=client) as streams,
        ClientSession(*streams) as session,
    ):
        await session.initialize()
        result = await session.call_tool("disconnect_google", {"account_ref": account})
        return result.structured_content


async def test_two_principals_cannot_read_decrypt_or_delete_other_grant(
    security_app, connect_google, principal_a, principal_b
):
    ctx = security_app
    await connect_google("user_alpha", "FAKE_account_a")
    await connect_google("user_beta", "FAKE_account_b")
    assert ctx.store.get(principal_b, "FAKE_account_a") is None
    row = ctx.store.get(principal_a, "FAKE_account_a")
    assert row
    with pytest.raises(AppError):
        decrypt_token(row[1], principal=principal_b, keyring=ctx.ring)
    denied = await disconnect(ctx, "user_beta", "FAKE_account_a")
    assert denied["error"]["code"] == "NOT_FOUND_OR_UNAVAILABLE"
    assert ctx.store.get(principal_a, "FAKE_account_a") == row
    success = await disconnect(ctx, "user_beta", "FAKE_account_b")
    assert success["data"]["disconnected"]
    assert ctx.store.get(principal_b, "FAKE_account_b") is None
    assert ctx.store.get(principal_a, "FAKE_account_a")
    with session_scope(ctx.engine) as session:
        repo = GrantRepo(ScopedSession(session, principal_b))
        with pytest.raises(AppError):
            repo.get(principal_a)
    same_subject_other_issuer = Principal("https://other.example.invalid", principal_a.subject)
    assert ctx.store.get(same_subject_other_issuer, "FAKE_account_a") is None


async def test_cache_keys_are_scoped_and_negative_test_detects_broken_filter(
    security_app, connect_google, principal_a, principal_b, monkeypatch
):
    ctx = security_app
    await connect_google()
    with session_scope(ctx.engine) as session:
        CacheStore(ScopedSession(session, principal_a), clock=ctx.clock).put(
            "FAKE_kind", "FAKE_shared_id", {"owner": "alpha"}
        )
    with session_scope(ctx.engine) as session:
        cache = CacheStore(ScopedSession(session, principal_b), clock=ctx.clock)
        assert cache.get("FAKE_kind", "FAKE_shared_id") is None
        assert cache.get_many("FAKE_kind", ["FAKE_shared_id"]) == {}
    # Prove the same read assertion detects a removed scoping predicate.
    with monkeypatch.context() as broken:
        broken.setattr(ScopedSession, "select", lambda self, model: select(model))
        with session_scope(ctx.engine) as session:
            leaked = CacheStore(ScopedSession(session, principal_b), clock=ctx.clock)
            with pytest.raises(AssertionError):
                assert leaked.get("FAKE_kind", "FAKE_shared_id") is None
            assert session.scalar(select(GoogleGrantRecord)) is not None
    # Restoration is scoped to this test, and the production predicate is checked again.
    with session_scope(ctx.engine) as session:
        assert (
            CacheStore(ScopedSession(session, principal_b)).get("FAKE_kind", "FAKE_shared_id")
            is None
        )
