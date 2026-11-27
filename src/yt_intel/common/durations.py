import re


class DurationParseError(ValueError):
    """The value is outside the supported integer-duration profile."""


_DURATION = re.compile(
    r"P(?:(?P<days>[0-9]+)D)?(?:T(?:(?P<hours>[0-9]+)H)?"
    r"(?:(?P<minutes>[0-9]+)M)?(?:(?P<seconds>[0-9]+)S)?)?"
)


def parse_iso8601_duration(value: str) -> int:
    match = _DURATION.fullmatch(value) if isinstance(value, str) else None
    if not match or value in {"P", "PT"} or value.endswith("T"):
        raise DurationParseError("Expected whole days, hours, minutes or seconds in ISO 8601 order")
    try:
        days, hours, minutes, seconds = (int(n or 0) for n in match.groups())
    except ValueError as exc:
        raise DurationParseError("Duration component exceeds the supported integer size") from exc
    return ((days * 24 + hours) * 60 + minutes) * 60 + seconds


def duration_seconds_or_none(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return parse_iso8601_duration(value)
    except DurationParseError:
        return None
