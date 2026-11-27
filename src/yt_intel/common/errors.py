"""Error codes and AppError — §0.4 interface contract (stub for D's implementation)."""

from __future__ import annotations

from enum import StrEnum
from typing import Any


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
    """Application-level error with structured code and optional retry hint."""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        *,
        details: dict[str, Any] | None = None,
        retryable: bool = False,
        retry_after: int | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details
        self.retryable = retryable
        self.retry_after = retry_after

    def to_dict(self, request_id: str | None = None) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details,
            "retryable": self.retryable,
            "retry_after": self.retry_after,
            "request_id": request_id,
        }
