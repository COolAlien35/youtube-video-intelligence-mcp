import json
from enum import StrEnum
from typing import Any

from ._redaction import redact, redact_text


class ErrorCode(StrEnum):
    INVALID_INPUT = "INVALID_INPUT"
    NOT_FOUND_OR_UNAVAILABLE = "NOT_FOUND_OR_UNAVAILABLE"
    AUTH_REQUIRED = "AUTH_REQUIRED"
    AUTH_EXPIRED_OR_REVOKED = "AUTH_EXPIRED_OR_REVOKED"
    CHANNEL_REQUIRED = "CHANNEL_REQUIRED"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"
    RATE_LIMITED = "RATE_LIMITED"
    NO_COMPLIANT_PLAYLIST = "NO_COMPLIANT_PLAYLIST"
    STALE_APPROVAL = "STALE_APPROVAL"
    WRITE_UNCERTAIN = "WRITE_UNCERTAIN"
    FORBIDDEN = "FORBIDDEN"
    POLICY_GATE_CLOSED = "POLICY_GATE_CLOSED"
    UPSTREAM_ERROR = "UPSTREAM_ERROR"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class AppError(Exception):
    """Supply a public message and JSON details, never raw exception output."""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        *,
        details: dict[str, Any] | None = None,
        retryable: bool = False,
        retry_after: int | None = None,
    ) -> None:
        self.message = redact_text(message)
        super().__init__(self.message)
        self.code = code
        self.details = redact(json.loads(json.dumps(details, allow_nan=False)))
        self.retryable = retryable
        self.retry_after = retry_after

    def to_dict(self, request_id: str | None = None) -> dict[str, Any]:
        return {
            "code": self.code.value,
            "message": self.message,
            "details": redact(self.details),
            "retryable": self.retryable,
            "retry_after": self.retry_after,
            "request_id": redact_text(request_id) if request_id else request_id,
        }
