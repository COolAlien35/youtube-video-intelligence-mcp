import asyncio
import inspect

import pytest
from mcp.server import MCPServer

from yt_intel.common import request_id_var
from yt_intel.tools.registry import TOOLS, register_tools

pytestmark = pytest.mark.unit
ALLOWED = {
    "similar_videos",
    "similar_channels",
    "recommendations",
    "engagement_analysis",
    "propose_playlist",
    "confirm_execute_playlist",
    "operation_status",
    "disconnect",
    "delete_data",
}


def test_tool_catalogue():
    server = MCPServer("test")
    register_tools(server)
    tools = asyncio.run(server.list_tools())
    assert len(tools) == 9 and {t.name for t in tools} == ALLOWED
    for tool in tools:
        assert tool.description and tool.input_schema["type"] == "object"
        assert "principal" not in tool.input_schema.get("properties", {})
        assert tool.output_schema


@pytest.mark.parametrize("handler", TOOLS)
def test_stub(handler):
    token = request_id_var.set("synthetic-request")
    try:
        args = {
            n: "synthetic"
            for n, p in inspect.signature(handler).parameters.items()
            if p.default is inspect.Parameter.empty
        }
        args.update(principal=None)
        if "max_total_seconds" in args:
            args["max_total_seconds"] = 60
        envelope = asyncio.run(handler(**args)).model_dump()
        assert set(envelope) == {"ok", "data", "error", "request_id"}
        assert envelope["ok"] is False and envelope["data"] is None
        assert envelope["error"]["code"] == "NOT_IMPLEMENTED"
        assert envelope["request_id"] == envelope["error"]["request_id"] == "synthetic-request"
    finally:
        request_id_var.reset(token)
