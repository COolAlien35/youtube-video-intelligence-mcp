from starlette.datastructures import Headers
from starlette.types import ASGIApp, Receive, Scope, Send

from yt_intel.common import AppError, ErrorCode

from .errors import error_response


class OriginMiddleware:
    def __init__(self, app: ASGIApp, allowed: list[str]) -> None:
        self.app = app
        self.allowed = frozenset(allowed)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            origins = Headers(scope=scope).getlist("origin")
            if origins and (len(origins) != 1 or origins[0] not in self.allowed):
                await error_response(AppError(ErrorCode.FORBIDDEN, "Origin is not allowed"))(
                    scope, receive, send
                )
                return
        await self.app(scope, receive, send)
