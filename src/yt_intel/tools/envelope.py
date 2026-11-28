from typing import Annotated, Any

from mcp.server.mcpserver import Resolve
from pydantic import BaseModel

from yt_intel.common import AppError, ErrorCode, Principal, get_request_id
from yt_intel.server.guards import get_principal

BoundPrincipal = Annotated[Principal | None, Resolve(get_principal)]


class ToolEnvelope(BaseModel):
    ok: bool
    data: dict[str, Any] | None
    error: dict[str, Any] | None
    request_id: str


def unavailable() -> ToolEnvelope:
    rid = get_request_id()
    if rid is None:
        raise RuntimeError("Tool invoked outside request context")
    error = AppError(ErrorCode.NOT_IMPLEMENTED, "This tool is not implemented yet")
    return ToolEnvelope(ok=False, data=None, error=error.to_dict(rid), request_id=rid)
