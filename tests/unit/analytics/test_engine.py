from datetime import UTC, datetime

import pytest

from yt_intel.analytics.engine import Observation, Window, analyze, duration_band


@pytest.mark.parametrize(
    "seconds,band",
    [
        (599, "under_10m"),
        (600, "10_to_under_30m"),
        (1799, "10_to_under_30m"),
        (1800, "30_to_60m"),
        (3599, "30_to_60m"),
        (3600, "30_to_60m"),
        (3601, "over_60m"),
        (None, "unknown"),
        (-1, "unknown"),
        (True, "unknown"),
        (1.2, "unknown"),
    ],
)
def test_duration_edges(seconds, band):
    assert duration_band(seconds) == band


def test_hand_count_and_distributions():
    period = Window(datetime(2025, 12, 31, tzinfo=UTC), datetime(2026, 1, 1, tzinfo=UTC))
    rows = [
        Observation("2026-01-01T00:30:00+05:30", channel_id="b"),
        Observation(period.start, channel_id="a", category_id="42", category_name="Supplied"),
        Observation(period.end),
        Observation("bad"),
        Observation(None),
    ]
    result = analyze("liked_videos", rows, period, top_n=1)
    assert result.count == 2 and result.excluded_invalid_timestamp == 2
    assert result.daily_counts == {"2025-12-31": 2}
    assert result.channels.distinct_known == 2 and result.channels.buckets[0].id == "a"
    assert result.channels.other_count == 1 and result.channels.other_share == 0.5
    assert [(b.id, b.name) for b in result.categories.buckets] == [
        ("42", "Supplied"),
        ("unknown", None),
    ]
    assert result.comparison.relative_change is None and result.comparison.absolute_change == 2
    assert analyze("subscriptions", rows, period).duration_bands == "not_applicable"
    custom = Window(period.end, datetime(2026, 1, 2, tzinfo=UTC))
    assert analyze("liked_videos", rows, period, custom).comparison.relative_change == 1
