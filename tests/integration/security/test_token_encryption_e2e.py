from urllib.parse import parse_qs, urlsplit

import pytest

from yt_intel.common import AppError
from yt_intel.common.errors import ReauthorizationRequiredError
from yt_intel.google_oauth.client import READ, WRITE
from yt_intel.security.crypto import KeyRing, decrypt_token, rotate_blob
from yt_intel.storage import session_scope
from yt_intel.storage.grants import GrantRepo
from yt_intel.storage.scoped import ScopedSession

pytestmark = pytest.mark.security


async def test_callback_persists_ciphertext_scopes_and_key_rotation(
    security_app, connect_google, principal_a, principal_b
):
    ctx = security_app
    result, query, _ = await connect_google()
    assert set(query["scope"][0].split()) == {"openid", READ}
    assert WRITE not in result.json()["scopes"]
    row = ctx.store.get(principal_a, "FAKE_google_alpha")
    assert row
    _, blob = row
    token = decrypt_token(blob, principal=principal_a, keyring=ctx.ring)
    with pytest.raises(AppError):
        decrypt_token(blob, principal=principal_b, keyring=ctx.ring)
    with session_scope(ctx.engine) as session:
        grant = GrantRepo(ScopedSession(session, principal_a)).get(principal_a)
        assert set(grant.granted_scopes.split()) == {"openid", READ}
        assert grant.ciphertext != token.encode() and grant.key_version == 1
    with ctx.engine.connect() as connection:
        connection.exec_driver_sql("PRAGMA wal_checkpoint(TRUNCATE)")
    database_files = [p for p in ctx.data_dir.rglob("*") if p.is_file()]
    assert database_files
    assert all(token.encode() not in path.read_bytes() for path in database_files)
    ring = KeyRing({1: b"1" * 32, 2: b"2" * 32}, active_version=2)
    assert decrypt_token(blob, principal=principal_a, keyring=ring) == token
    rotated = rotate_blob(blob, principal=principal_a, keyring=ring)
    ctx.store.save(principal_a, row[0], frozenset(result.json()["scopes"]), rotated)
    stored = ctx.store.get(principal_a, row[0])[1]
    assert stored.key_version == 2 and stored.ciphertext != blob.ciphertext
    assert (
        decrypt_token(
            stored, principal=principal_a, keyring=KeyRing({2: b"2" * 32}, active_version=2)
        )
        == token
    )


async def test_fake_testing_grant_requires_reauthorization_after_seven_days(
    security_app, connect_google, principal_a
):
    ctx = security_app
    await connect_google()
    blob = ctx.store.get(principal_a, "FAKE_google_alpha")[1]
    token = decrypt_token(blob, principal=principal_a, keyring=ctx.ring)
    assert (await ctx.google.refresh(token)).access_token
    ctx.clock.advance(7 * 24 * 3600)
    with pytest.raises(ReauthorizationRequiredError):
        await ctx.google.refresh(token)


@pytest.mark.parametrize("failure", ["state", "expired", "principal", "redirect", "pkce"])
async def test_callback_binding_rejects_without_persisting_grant(security_app, failure):
    ctx = security_app
    start = await ctx.browser.get(
        "/oauth/google/start", headers={"Authorization": "Bearer " + ctx.issuer.mint()}
    )
    query = parse_qs(urlsplit(start.headers["location"]).query)
    challenge = "FAKE_wrong_challenge" if failure == "pkce" else query["code_challenge"][0]
    code = ctx.google.authorize(challenge)
    params = {"state": query["state"][0], "code": code}
    headers = {}
    if failure == "state":
        params["state"] = "FAKE_wrong_state"
    elif failure == "expired":
        ctx.link.now = lambda: float("inf")
    elif failure == "principal":
        headers["Authorization"] = "Bearer " + ctx.issuer.mint("user_beta")
    elif failure == "redirect":
        headers["Host"] = "other.example.invalid"
    response = await ctx.browser.get("/oauth/google/callback", params=params, headers=headers)
    assert response.status_code in {400, 401, 403}
    assert ctx.store.get(ctx.verifier.verify(ctx.issuer.mint()), "synthetic-google") is None


async def test_callback_is_single_use(security_app, connect_google):
    ctx = security_app
    _, query, code = await connect_google()
    replay = await ctx.browser.get(
        "/oauth/google/callback", params={"state": query["state"][0], "code": code}
    )
    assert replay.status_code == 401
