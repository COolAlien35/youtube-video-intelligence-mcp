from typing import Any

from pydantic import BaseModel

from yt_intel.common import AppError, get_request_id
from yt_intel.server.auth import application_state
from yt_intel.services.similar_videos import SimilarVideosResult, SimilarVideosService

from .envelope import BoundPrincipal


class SimilarVideosEnvelope(BaseModel):
    ok: bool
    data: SimilarVideosResult | None
    error: dict[str, Any] | None
    request_id: str


async def similar_videos(seed: str, *, principal: BoundPrincipal) -> SimilarVideosEnvelope:
    """Find videos with similar metadata using an exact YouTube video ID or URL."""
    request_id = get_request_id()
    if request_id is None:
        raise RuntimeError("Tool invoked outside request context")
    service: SimilarVideosService = application_state.get().similar_videos
    try:
        data = await service.run(principal, seed)
    except AppError as exc:
        return SimilarVideosEnvelope(
            ok=False, error=exc.to_dict(request_id), data=None, request_id=request_id
        )
    return SimilarVideosEnvelope(ok=True, data=data, error=None, request_id=request_id)
