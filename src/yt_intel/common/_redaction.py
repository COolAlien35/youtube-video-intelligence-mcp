"""Redact credential fields and recognizable token formats at output boundaries."""

import re
from typing import Any

_MASK = "[REDACTED]"
_FIELD = (
    r"(?:refresh[_-]?token|access[_-]?token|client[_-]?secret"
    r"|api[_-]?key|token|secret|password|authorization)"
)
_SECRET_FIELDS = re.compile(_FIELD + r"|stack[_-]?trace|traceback|exc_info", re.I)
_TOKEN = re.compile(
    r"Bearer\s+[^\s,;\"'\]}]+"
    r"|AIza[A-Za-z0-9_-]{20,}|ya29\.[\w.-]+|eyJ[\w-]+\.[\w-]+\.[\w-]+",
    re.I,
)
_ASSIGNMENT = re.compile(
    rf"""(?P<label>\b{_FIELD}["']?\s*[:=]\s*)(?:"[^"]*"|'[^']*'|[^\s,;}}\]]+)""", re.I
)


def redact_text(value: str) -> str:
    return _ASSIGNMENT.sub(r"\g<label>[REDACTED]", _TOKEN.sub(_MASK, value))


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            redact_text(str(k)): _MASK if _SECRET_FIELDS.fullmatch(str(k)) else redact(v)
            for k, v in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact(v) for v in value]
    return redact_text(value) if isinstance(value, str) else value
