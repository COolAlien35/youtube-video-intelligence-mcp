from datetime import UTC, date, datetime
from typing import Any

from pydantic import BaseModel, ValidationError

from yt_intel.analytics.engine import Window
from yt_intel.common import AppError, ErrorCode, get_request_id
from yt_intel.common.timeutil import parse_rfc3339_utc
from yt_intel.server.auth import application_state
from yt_intel.services.engagement import EngagementRequest, EngagementResult, EngagementService

from .envelope import BoundPrincipal


class Period(BaseModel):
    start: str
    end: str

    def window(self) -> Window:
        def boundary(text: str) -> datetime:
            if len(text) == 10:
                return datetime.combine(date.fromisoformat(text), datetime.min.time(), UTC)
            return parse_rfc3339_utc(text)

        return Window(boundary(self.start), boundary(self.end))


class EngagementEnvelope(BaseModel):
    ok: bool
    data: EngagementResult | None
    error: dict[str, Any] | None
    request_id: str


async def engagement_analysis(
    source: str,
    period: Period,
    *,
    principal: BoundPrincipal,
    playlist_id: str | None = None,
    compare_to: Period | None = None,
) -> EngagementEnvelope:
    """Describe liked videos, subscriptions or playlist items in a UTC period."""
    rid = get_request_id()
    if rid is None:
        raise RuntimeError("Tool invoked outside request context")
    try:
        try:
            req = EngagementRequest.model_validate(
                {
                    "source": source,
                    "period": period.window(),
                    "playlist_id": playlist_id,
                    "compare_to": compare_to.window() if compare_to else None,
                }
            )
        except (ValueError, ValidationError, OverflowError):
            raise AppError(
                ErrorCode.INVALID_INPUT, "Invalid account source, playlist or period"
            ) from None
        service: EngagementService = application_state.get().engagement
        result = await service.run(principal, req)
    except AppError as exc:
        return EngagementEnvelope(ok=False, data=None, error=exc.to_dict(rid), request_id=rid)
    return EngagementEnvelope(ok=True, data=result, error=None, request_id=rid)
