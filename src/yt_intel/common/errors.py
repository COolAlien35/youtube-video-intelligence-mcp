import json
from enum import StrEnum
from typing import Any

from ._redaction import redact, redact_text


class ErrorCode(StrEnum):
    RECONCILIATION_AMBIGUOUS = "RECONCILIATION_AMBIGUOUS"
    CONSTRAINT_VIOLATION = "CONSTRAINT_VIOLATION"
    INVALID_TRANSITION = "INVALID_TRANSITION"
    APPROVAL_INVALID = "APPROVAL_INVALID"
    PROPOSAL_EXPIRED = "PROPOSAL_EXPIRED"
    PROPOSAL_NOT_FOUND = "PROPOSAL_NOT_FOUND"
    WRITE_SCOPE_REQUIRED = "WRITE_SCOPE_REQUIRED"
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
    POLICY_GATE_CLOSED = "policy_gate_closed"
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


class AuthRequiredError(AppError):
    def __init__(self) -> None:
        super().__init__(ErrorCode.AUTH_REQUIRED, "Authentication required")


class InvalidTokenError(AppError):
    def __init__(self) -> None:
        super().__init__(ErrorCode.AUTH_REQUIRED, "Invalid service access token")


class ForbiddenOriginError(AppError):
    def __init__(self) -> None:
        super().__init__(ErrorCode.FORBIDDEN, "Origin is not allowed")


class ReauthorizationRequiredError(AppError):
    def __init__(self) -> None:
        super().__init__(ErrorCode.AUTH_EXPIRED_OR_REVOKED, "Reconnect the Google account")


class TenantViolationError(AppError):
    def __init__(self) -> None:
        super().__init__(ErrorCode.FORBIDDEN, "Access denied")


class PolicyGateClosedError(AppError):
    def __init__(self) -> None:
        super().__init__(ErrorCode.POLICY_GATE_CLOSED, "Policy clearance is required")


class ChannelRequiredError(AppError):
    def __init__(self) -> None:
        super().__init__(
            ErrorCode.CHANNEL_REQUIRED,
            "A YouTube channel is required",
            details={"next_step": "Create a YouTube channel and start a new proposal"},
        )


class WriteScopeRequiredError(AppError):
    def __init__(self) -> None:
        super().__init__(
            ErrorCode.WRITE_SCOPE_REQUIRED,
            "Playlist write scope is required",
            details={"next_step": "Request incremental consent for playlist writes"},
        )


class ProposalNotFoundError(AppError):
    def __init__(self) -> None:
        super().__init__(ErrorCode.PROPOSAL_NOT_FOUND, "Proposal unavailable")


class ProposalExpiredError(AppError):
    def __init__(self) -> None:
        super().__init__(ErrorCode.PROPOSAL_EXPIRED, "Proposal expired")


class ApprovalInvalidError(AppError):
    def __init__(self) -> None:
        super().__init__(ErrorCode.APPROVAL_INVALID, "Approval is invalid")


class InvalidTransitionError(AppError):
    def __init__(self) -> None:
        super().__init__(
            ErrorCode.INVALID_TRANSITION, "Operation state does not permit this transition"
        )


class ConstraintViolationError(AppError):
    def __init__(self) -> None:
        super().__init__(ErrorCode.CONSTRAINT_VIOLATION, "Playlist constraints cannot be satisfied")


class OutcomeUncertainError(AppError):
    def __init__(self) -> None:
        super().__init__(ErrorCode.WRITE_UNCERTAIN, "Write outcome is uncertain")


class ReconciliationAmbiguousError(AppError):
    def __init__(self) -> None:
        super().__init__(
            ErrorCode.RECONCILIATION_AMBIGUOUS, "Reconciliation found multiple possible matches"
        )
