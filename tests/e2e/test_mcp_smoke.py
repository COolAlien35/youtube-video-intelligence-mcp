import asyncio

import httpx2
import pytest
from mcp.client import ClientSession
from mcp.client.streamable_http import streamable_http_client
from yt_intel.config import Settings

from yt_intel.server.app import create_app

pytestmark = pytest.mark.e2e


@pytest.mark.parametrize("legacy", [False, True], ids=["july-discovery", "legacy-initialize"])
def test_mcp_smoke(legacy):
    origin = "http://localhost:8000"
    app = create_app(Settings(_env_file=None, allowed_origins=[origin]))
    responses = []

    async def remember(response):
        responses.append(response.headers["x-request-id"])

    async def run():
        async with (
            app.router.lifespan_context(app),
            httpx2.AsyncClient(
                transport=httpx2.ASGITransport(app=app),
                base_url=origin,
                headers={"Origin": origin},
                event_hooks={"response": [remember]},
            ) as http,
            streamable_http_client(origin + "/mcp", http_client=http) as streams,
            ClientSession(*streams) as session,
        ):
            if legacy:
                await session.initialize()
            else:
                result = await session.discover()
                assert "2026-07-28" in result.supported_versions
            catalogue = await session.list_tools()
            assert len(catalogue.tools) == 9
            response = await session.call_tool("similar_videos", {"seed": "FAKE_vid-01"})
            data = response.structured_content
            assert data and data["error"]["code"] == "NOT_IMPLEMENTED"
            assert data["request_id"] == data["error"]["request_id"] == responses[-1]

    asyncio.run(run())
