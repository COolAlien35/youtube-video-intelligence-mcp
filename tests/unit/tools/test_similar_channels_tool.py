import json
from pathlib import Path

import httpx2
import jsonschema
from mcp.client import ClientSession
from mcp.client.streamable_http import streamable_http_client
from tests.support.b_auth import FakeIssuer

from yt_intel.config import Settings
from yt_intel.server.app import create_app


async def test_registered_tool_schemas_and_principal(tmp_path):
    origin = "http://localhost:8000"
    issuer = FakeIssuer()
    app = create_app(Settings(_env_file=None, data_dir=tmp_path), verifier=issuer.verifier())
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
            tool = next(
                t for t in (await session.list_tools()).tools if t.name == "similar_channels"
            )
            for kind, schema in [("input", tool.input_schema), ("output", tool.output_schema)]:
                path = (
                    Path(__file__).resolve().parents[3]
                    / "docs/tools"
                    / f"similar_channels.{kind}.schema.json"
                )
                assert schema == json.loads(path.read_text())
            assert set(tool.input_schema["properties"]) == {"channel"}
            for ref, error in [
                ("@syn_prism", None),
                ("youtube.com/c/legacy", "INVALID_INPUT"),
                ("@no_match", "NOT_FOUND_OR_UNAVAILABLE"),
            ]:
                response = (await session.call_tool(tool.name, {"channel": ref})).structured_content
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
