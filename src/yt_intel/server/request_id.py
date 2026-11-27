import logging
from time import monotonic

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from yt_intel.common import AppError, ErrorCode, new_request_id, request_id_var

from .errors import error_response

log = logging.getLogger(__name__)


class RequestIDMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        rid = new_request_id()
        token = request_id_var.set(rid)
        start = monotonic()
        status = 0

        async def correlated(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                MutableHeaders(scope=message)["X-Request-ID"] = rid
            await send(message)

        try:
            await self.app(scope, receive, correlated)
        except Exception:
            log.exception("Unhandled request error")
            if status:
                raise
            await error_response(AppError(ErrorCode.INTERNAL_ERROR, "Internal server error"))(
                scope, receive, correlated
            )
        finally:
            try:
                log.info(
                    "HTTP request",
                    extra={
                        "method": scope["method"],
                        "path": scope["path"],
                        "status": status,
                        "duration_ms": round((monotonic() - start) * 1000, 2),
                    },
                )
            finally:
                request_id_var.reset(token)
