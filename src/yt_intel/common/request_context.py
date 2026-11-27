"""Request-context var — §0.4 interface contract (stub for D's implementation)."""

from __future__ import annotations

import uuid
from contextvars import ContextVar

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)


def new_request_id() -> str:
    """Generate and store a fresh request ID in the current context."""
    rid = str(uuid.uuid4())
    request_id_var.set(rid)
    return rid


def get_request_id() -> str | None:
    """Return the current request ID, or None if not set."""
    return request_id_var.get()


def set_request_id(rid: str | None) -> None:
    """Set the request ID for the current context."""
    request_id_var.set(rid)
