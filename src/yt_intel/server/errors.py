from fastapi import Request
from starlette.responses import JSONResponse

from yt_intel.common import AppError, ErrorCode, get_request_id

HTTP_STATUS = {
    ErrorCode.RECONCILIATION_AMBIGUOUS: 409,
    ErrorCode.CONSTRAINT_VIOLATION: 422,
    ErrorCode.INVALID_TRANSITION: 409,
    ErrorCode.APPROVAL_INVALID: 403,
    ErrorCode.PROPOSAL_EXPIRED: 410,
    ErrorCode.PROPOSAL_NOT_FOUND: 404,
    ErrorCode.WRITE_SCOPE_REQUIRED: 403,
    ErrorCode.INVALID_INPUT: 400,
    ErrorCode.NOT_FOUND_OR_UNAVAILABLE: 404,
    ErrorCode.AUTH_REQUIRED: 401,
    ErrorCode.AUTH_EXPIRED_OR_REVOKED: 401,
    ErrorCode.CHANNEL_REQUIRED: 409,
    ErrorCode.QUOTA_EXCEEDED: 429,
    ErrorCode.RATE_LIMITED: 429,
    ErrorCode.NO_COMPLIANT_PLAYLIST: 422,
    ErrorCode.STALE_APPROVAL: 409,
    ErrorCode.WRITE_UNCERTAIN: 409,
    ErrorCode.FORBIDDEN: 403,
    ErrorCode.POLICY_GATE_CLOSED: 403,
    ErrorCode.UPSTREAM_ERROR: 502,
    ErrorCode.NOT_IMPLEMENTED: 501,
    ErrorCode.INTERNAL_ERROR: 500,
}


def error_response(error: AppError) -> JSONResponse:
    return JSONResponse(error.to_dict(get_request_id()), status_code=HTTP_STATUS[error.code])


async def handle_app_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)
    return error_response(exc)
