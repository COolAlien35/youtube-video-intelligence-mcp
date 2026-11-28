from typing import Any

from pydantic import BaseModel

from yt_intel.common import AppError, get_request_id
from yt_intel.server.auth import application_state
from yt_intel.services.similar_channels import SimilarChannelsResult, SimilarChannelsService

from .envelope import BoundPrincipal


class SimilarChannelsEnvelope(BaseModel):
    ok: bool
    data: SimilarChannelsResult | None
    error: dict[str, Any] | None
    request_id: str


async def similar_channels(channel: str, *, principal: BoundPrincipal) -> SimilarChannelsEnvelope:
    """Find channels with similar metadata using an exact YouTube channel ID, handle or URL."""
    request_id = get_request_id()
    if request_id is None:
        raise RuntimeError("Tool invoked outside request context")
    service: SimilarChannelsService = application_state.get().similar_channels
    try:
        data = await service.run(principal, channel)
    except AppError as exc:
        return SimilarChannelsEnvelope(
            ok=False, error=exc.to_dict(request_id), data=None, request_id=request_id
        )
    return SimilarChannelsEnvelope(ok=True, data=data, error=None, request_id=request_id)
