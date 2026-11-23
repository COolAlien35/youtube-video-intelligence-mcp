from yt_intel.common.errors import AppError, ErrorCode

REASONS = {
    "invalidParameter": ErrorCode.INVALID_INPUT,
    "badRequest": ErrorCode.INVALID_INPUT,
    "videoNotFound": ErrorCode.NOT_FOUND_OR_UNAVAILABLE,
    "playlistNotFound": ErrorCode.NOT_FOUND_OR_UNAVAILABLE,
    "channelNotFound": ErrorCode.NOT_FOUND_OR_UNAVAILABLE,
    "invalid_grant": ErrorCode.AUTH_EXPIRED_OR_REVOKED,
    "youtubeSignupRequired": ErrorCode.CHANNEL_REQUIRED,
    "quotaExceeded": ErrorCode.QUOTA_EXCEEDED,
    "rateLimitExceeded": ErrorCode.RATE_LIMITED,
    "forbidden": ErrorCode.FORBIDDEN,
}


def map_api_error(status: int, reason: str) -> AppError:
    fallback = {
        400: ErrorCode.INVALID_INPUT,
        401: ErrorCode.AUTH_REQUIRED,
        403: ErrorCode.FORBIDDEN,
        404: ErrorCode.NOT_FOUND_OR_UNAVAILABLE,
        429: ErrorCode.RATE_LIMITED,
    }
    code = REASONS.get(reason, fallback.get(status, ErrorCode.UPSTREAM_ERROR))
    return AppError(
        code,
        code.value.replace("_", " ").capitalize(),
        retryable=code == ErrorCode.RATE_LIMITED or status >= 500,
    )
