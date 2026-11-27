"""Application-owned root logging configuration for the server entry point."""

import json
import logging
from datetime import UTC, datetime
from typing import Any

from ._redaction import redact
from .request_context import get_request_id
from .timeutil import format_utc

_STANDARD = frozenset(logging.makeLogRecord({}).__dict__) | {"asctime", "message"}
_PRIVATE = {
    "headers",
    "body",
    "request_headers",
    "request_body",
    "response_headers",
    "response_body",
}


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        event: dict[str, Any] = {
            "timestamp": format_utc(datetime.fromtimestamp(record.created, UTC)),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": get_request_id(),
        }
        extra = {
            k: v
            for k, v in vars(record).items()
            if k not in _STANDARD and k.lower() not in _PRIVATE
        }
        if extra:
            event["extra"] = extra
        if record.exc_info and record.exc_info[1] is not None:
            event["exception"] = str(record.exc_info[1])
        return json.dumps(redact(event), default=lambda _: "[unsupported]", ensure_ascii=True)


def configure_logging(level: str = "INFO") -> None:
    """Install a single JSON handler on the root logger at application startup."""
    root = logging.getLogger()
    root.setLevel(level.upper())
    if len(root.handlers) == 1 and isinstance(root.handlers[0].formatter, _JsonFormatter):
        return
    handler = logging.StreamHandler()
    handler.setFormatter(_JsonFormatter())
    logging.basicConfig(handlers=[handler], force=True)
