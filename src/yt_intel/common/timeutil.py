import re
from datetime import UTC, datetime

_TIMESTAMP = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}[Tt][0-9]{2}:[0-5][0-9]:[0-5][0-9]"
    r"(?:\.[0-9]+)?(?:[Zz]|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])"
)


def parse_rfc3339_utc(value: str) -> datetime:
    if not _TIMESTAMP.fullmatch(value):
        raise ValueError("Expected an RFC 3339 timestamp with timezone")
    return datetime.fromisoformat(value.upper()).astimezone(UTC)


def format_utc(value: datetime) -> str:
    if value.utcoffset() is None:
        raise ValueError("A timezone is required")
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
