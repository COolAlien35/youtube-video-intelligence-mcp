"""Pure descriptive statistics for authorized, timestamped account signals."""

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from yt_intel.common.timeutil import parse_rfc3339_utc

Source = Literal["liked_videos", "subscriptions", "playlist_items"]
BANDS = ("under_10m", "10_to_under_30m", "30_to_60m", "over_60m", "unknown")


def utc(value: object) -> datetime | None:
    try:
        if isinstance(value, str):
            return parse_rfc3339_utc(value)
        if isinstance(value, datetime) and value.utcoffset() is not None:
            return value.astimezone(UTC)
    except (ValueError, OverflowError):
        pass
    return None


@dataclass(frozen=True)
class Window:
    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        start, end = utc(self.start), utc(self.end)
        if start is None or end is None or start >= end:
            raise ValueError("Expected an ordered timezone-aware period")
        object.__setattr__(self, "start", start)
        object.__setattr__(self, "end", end)


@dataclass(frozen=True)
class Observation:
    timestamp: datetime | str | None
    video_id: str | None = None
    channel_id: str | None = None
    category_id: str | None = None
    category_name: str | None = None
    duration_seconds: int | None = None


def duration_band(seconds: object) -> str:
    if type(seconds) is not int or seconds < 0:
        return "unknown"
    if seconds < 600:
        return BANDS[0]
    if seconds < 1800:
        return BANDS[1]
    return BANDS[2] if seconds <= 3600 else BANDS[3]


@dataclass(frozen=True)
class Bucket:
    id: str
    count: int
    share: float
    name: str | None = None


@dataclass(frozen=True)
class Distribution:
    buckets: list[Bucket]
    other_count: int
    other_share: float
    distinct_known: int


def distribution(values: list[tuple[str | None, str | None]], limit: int) -> Distribution:
    if limit < 1:
        raise ValueError("Expected a positive distribution limit")
    counts = Counter(key or "unknown" for key, _ in values)
    names = {key: name for key, name in values if key and name}
    ordered = sorted(counts, key=lambda key: (-counts[key], key))
    total = len(values)
    buckets = [
        Bucket(key, counts[key], counts[key] / total, names.get(key)) for key in ordered[:limit]
    ]
    other = sum(counts[key] for key in ordered[limit:])
    return Distribution(
        buckets, other, other / total if total else 0, len(counts.keys() - {"unknown"})
    )


@dataclass(frozen=True)
class Comparison:
    period: Window
    earlier_count: int
    absolute_change: int
    relative_change: float | None


@dataclass(frozen=True)
class Metrics:
    count: int
    excluded_invalid_timestamp: int
    daily_counts: dict[str, int]
    channels: Distribution
    categories: Distribution | Literal["not_applicable"]
    duration_bands: dict[str, int] | Literal["not_applicable"]
    comparison: Comparison


def analyze(
    source: Source,
    rows: Sequence[Observation],
    period: Window,
    compare_to: Window | None = None,
    *,
    top_n: int = 10,
) -> Metrics:
    previous = compare_to or Window(period.start - (period.end - period.start), period.start)
    selected = []
    days: Counter[str] = Counter()
    earlier = invalid = 0
    for row in rows:
        when = utc(row.timestamp)
        if when is None:
            invalid += 1
            continue
        earlier += int(previous.start <= when < previous.end)
        if period.start <= when < period.end:
            selected.append(row)
            days[when.date().isoformat()] += 1
    delta = len(selected) - earlier
    bands = Counter(duration_band(row.duration_seconds) for row in selected)
    return Metrics(
        len(selected),
        invalid,
        dict(sorted(days.items())),
        distribution([(row.channel_id, None) for row in selected], top_n),
        "not_applicable"
        if source == "subscriptions"
        else distribution(
            [(row.category_id, row.category_name) for row in selected], max(1, len(selected))
        ),
        "not_applicable" if source == "subscriptions" else {key: bands[key] for key in BANDS},
        Comparison(previous, earlier, delta, delta / earlier if earlier else None),
    )
