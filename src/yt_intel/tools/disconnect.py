from yt_intel.common import AppError, get_request_id
from yt_intel.server.auth import application_state
from yt_intel.server.oauth_routes import get_link

from .envelope import BoundPrincipal, ToolEnvelope


async def disconnect_google(account_ref: str, *, principal: BoundPrincipal) -> ToolEnvelope:
    """Revoke and delete the caller's grant for a linked Google account."""
    rid = get_request_id()
    if rid is None:
        raise RuntimeError("Tool invoked outside request context")
    try:
        link = get_link(application_state.get())
        data = await link.disconnect(principal, account_ref)
    except AppError as exc:
        return ToolEnvelope(ok=False, data=None, error=exc.to_dict(rid), request_id=rid)
    return ToolEnvelope(ok=True, data=dict(data), error=None, request_id=rid)
