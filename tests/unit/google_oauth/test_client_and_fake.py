from datetime import UTC, datetime
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest

from yt_intel.common import FakeClock
from yt_intel.common.errors import ReauthorizationRequiredError
from yt_intel.common.oauth_util import new_pkce_pair
from yt_intel.google_oauth.client import READ, WRITE, GoogleWebClient
from yt_intel.google_oauth.fake import FakeGoogleOAuth

pytestmark = [pytest.mark.unit, pytest.mark.security]
URI = "http://localhost/oauth/google/callback"


async def test_web_contract():
    def exchange(request):
        fields = parse_qs(request.content.decode())
        assert fields["code_verifier"] == ["FAKE_v"] and fields["redirect_uri"] == [URI]
        return httpx.Response(200, json={"access_token": "FAKE_access", "scope": READ})

    async with httpx.AsyncClient(transport=httpx.MockTransport(exchange)) as http:
        client = GoogleWebClient("synthetic", "FAKE_secret", URI, http)
        for write in [False, True]:
            q = parse_qs(urlsplit(client.build_auth_url("s", "c", write=write)).query)
            assert q["access_type"] == ["offline"] and q["code_challenge_method"] == ["S256"]
            assert (WRITE in q["scope"][0].split()) == write
        assert (await client.exchange_code("FAKE_code", "FAKE_v")).scopes == {READ}


async def test_invalid_grant():
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda r: httpx.Response(400, json={"error": "invalid_grant"})
        )
    ) as http:
        with pytest.raises(ReauthorizationRequiredError):
            await GoogleWebClient("synthetic", "FAKE_secret", URI, http).refresh("FAKE_refresh")


async def test_testing_expiry_and_partial_scopes():
    clock = FakeClock(datetime(2026, 1, 1, tzinfo=UTC))
    client = FakeGoogleOAuth(URI, clock)
    v, c = new_pkce_pair()
    client.partial_scopes = frozenset({"openid"})
    t = await client.exchange_code(client.authorize(c), v)
    assert t.scopes == {"openid"}
    assert await client.subject(t.access_token) == "synthetic-google"
    assert (await client.refresh(t.refresh_token)).access_token
    clock.advance(7 * 86400)
    with pytest.raises(ReauthorizationRequiredError):
        await client.refresh(t.refresh_token)
