import json
from pathlib import Path

import httpx2
import jsonschema
from mcp.client import ClientSession
from mcp.client.streamable_http import streamable_http_client
from tests.support.b_auth import FakeIssuer

from yt_intel.config import Settings
from yt_intel.provider.fixture import FaultPlan
from yt_intel.quota import QuotaPlan
from yt_intel.server.app import create_app


async def test_registered_tool_schemas_and_principal(tmp_path):
    origin = "http://localhost:8000"
    issuer = FakeIssuer()
    app = create_app(
        Settings(max_workflow_starts_per_minute=20, _env_file=None, data_dir=tmp_path),
        verifier=issuer.verifier(),
    )
    async with (
        app.router.lifespan_context(app),
        httpx2.AsyncClient(transport=httpx2.ASGITransport(app), base_url=origin) as client,
    ):
        assert (await client.post("/mcp")).status_code == 401
        client.headers["Authorization"] = "Bearer " + issuer.mint()
        async with (
            streamable_http_client(origin + "/mcp", http_client=client) as streams,
            ClientSession(*streams) as session,
        ):
            await session.initialize()
            tool = next(t for t in (await session.list_tools()).tools if t.name == "similar_videos")
            for kind, schema in [("input", tool.input_schema), ("output", tool.output_schema)]:
                path = (
                    Path(__file__).resolve().parents[3]
                    / "docs/tools"
                    / f"similar_videos.{kind}.schema.json"
                )
                assert schema == json.loads(path.read_text())
            assert set(tool.input_schema["properties"]) == {"seed"}
            for ref, error in [
                ("SYNV_000000", None),
                ("oops", "INVALID_INPUT"),
                ("SYNV_absent", "NOT_FOUND_OR_UNAVAILABLE"),
            ]:
                response = (await session.call_tool(tool.name, {"seed": ref})).structured_content
                jsonschema.validate(response, tool.output_schema)
                if error:
                    assert response["error"]["code"] == error
                    assert response["error"]["request_id"] == response["request_id"]
                else:
                    assert response["ok"] and response["data"]["items"]
                    assert (
                        "metadata" in response["data"]["provenance"]
                        and "YouTube" in response["data"]["source"]
                    )

            service = app.state.similar_videos
            owner = issuer.verifier().verify(issuer.mint())

            async def expect_denial(code):
                answer = (
                    await session.call_tool(tool.name, {"seed": "SYNV_000001"})
                ).structured_content
                assert answer["error"]["code"] == code
                assert answer["request_id"] == answer["error"]["request_id"]
                assert answer["data"] is None

            with service.limiter.acquire_workflow(owner), service.limiter.acquire_workflow(owner):
                await expect_denial("RATE_LIMITED")
            hold = service.planner.reserve(owner, QuotaPlan(0, 19))
            try:
                await expect_denial("QUOTA_EXCEEDED")
            finally:
                hold.release()
            service.provider.faults = FaultPlan(
                "get_videos", service.provider.calls["get_videos"] + 1
            )
            await expect_denial("UPSTREAM_ERROR")

            provider = service.provider
            provider.faults = None
            provider.raw["search.list/linear algebra-1"] = {
                "items": [{"id": {"videoId": "SYNV_000007"}}]
            }
            answer = (
                await session.call_tool(tool.name, {"seed": "SYNV_000001"})
            ).structured_content
            (item,) = answer["data"]["items"]
            assert item["title"] == provider.videos["SYNV_000007"].title
            assert provider.videos["SYNV_000007"].description not in item["explanation"]
            assert set(provider.calls) == {"get_videos", "search_videos"}
