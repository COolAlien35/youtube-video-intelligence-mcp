from datetime import UTC, datetime

import pytest

from yt_intel.common import AppError, ErrorCode
from yt_intel.common.durations import (
    DurationParseError,
    duration_seconds_or_none,
    parse_iso8601_duration,
)
from yt_intel.common.ids import ChannelRef, parse_channel_ref, parse_playlist_id, parse_video_id
from yt_intel.common.timeutil import format_utc, parse_rfc3339_utc

pytestmark = pytest.mark.unit
V = "FAKE_vid-01"
C = "UC" + "F" * 22
Y = "https://www.youtube.com"


@pytest.mark.parametrize(
    "ref",
    [
        V,
        f"{Y}/watch?v={V}&t=4",
        f"https://youtu.be/{V}?x=y",
        f"{Y}/shorts/{V}",
        f"{Y}/embed/{V}",
        f"{Y}/live/{V}",
        f"m.youtube.com/watch?v={V}",
    ],
)
def test_video_dedup(ref):
    assert parse_video_id(ref) == V


@pytest.mark.parametrize(
    "ref",
    [
        "",
        None,
        "A" * 10,
        "A" * 12,
        "bad!bad!bad",
        f"{Y}/watch",
        f"{Y}/watch?v={V}&v={V}",
        f"{Y}/watch?v=",
        f"{Y}/v/{V}",
        f"https://youtu.be/{V}/more",
        f"https://example.com/watch?v={V}",
        f"ftp://youtube.com/live/{V}",
        f"https://example.com@youtube.com/live/{V}",
        "https://[invalid",
        f"{Y}/watch?\nv={V}",
    ],
)
def test_invalid_video(ref):
    with pytest.raises(AppError) as err:
        parse_video_id(ref)
    assert err.value.code is ErrorCode.INVALID_INPUT


@pytest.mark.parametrize(
    "ref", ["PL_FAKE-01", f"{Y}/playlist?list=PL_FAKE-01", f"{Y}/watch?v={V}&list=PL_FAKE-01"]
)
def test_playlist(ref):
    assert parse_playlist_id(ref) == "PL_FAKE-01"


@pytest.mark.parametrize(
    "ref",
    [
        "",
        "A B",
        "PL!",
        "https://example.com/?list=PL",
        f"{Y}/playlist",
        f"{Y}/playlist?list=",
        f"{Y}/playlist?list=PL&list=PL",
        f"{Y}/playlist?list=a%2Fb",
    ],
)
def test_invalid_playlist(ref):
    with pytest.raises(AppError, match=r".+"):
        parse_playlist_id(ref)


@pytest.mark.parametrize(
    "ref,expected",
    [
        (C, ChannelRef("id", C)),
        (f"{Y}/channel/{C}", ChannelRef("id", C)),
        ("@FAKE.handle", ChannelRef("handle", "@FAKE.handle")),
        (f"{Y}/@FAKE-handle/", ChannelRef("handle", "@FAKE-handle")),
        (f"{Y}/@caf%C3%A9", ChannelRef("handle", "@café")),
        (f"{Y}/@Fake_User/videos", ChannelRef("handle", "@Fake_User")),
    ],
)
def test_channel(ref, expected):
    assert parse_channel_ref(ref) == expected


@pytest.mark.parametrize(
    "ref",
    [
        "",
        None,
        "@",
        "@a b",
        "guess",
        C[:-1],
        f"{Y}/c/legacy",
        f"{Y}/channel/oops",
        f"{Y}/user/Fake_User",
        f"{Y}/user/",
        f"{Y}/user/a/b",
        f"{Y}/@fake%2Fextra",
        "https://youtu.be/@fake",
    ],
)
def test_invalid_channel(ref):
    with pytest.raises(AppError) as err:
        parse_channel_ref(ref)
    assert err.value.code is ErrorCode.INVALID_INPUT


@pytest.mark.parametrize(
    "value,seconds",
    [
        ("PT0S", 0),
        ("PT45S", 45),
        ("PT1H2M3S", 3723),
        ("P1DT2H", 93600),
        ("P2D", 172800),
        ("PT1M", 60),
        ("PT02H", 7200),
        ("P1DT1S", 86401),
    ],
)
def test_duration(value, seconds):
    assert parse_iso8601_duration(value) == duration_seconds_or_none(value) == seconds


@pytest.mark.parametrize(
    "value",
    [
        "",
        "P",
        "PT",
        "P2DT",
        "PT1.5S",
        "PT-1S",
        "-PT1S",
        "P1W",
        "P1M",
        "P1Y",
        "P1S",
        "PT3M2H",
        "PT1S2S",
        "1:00",
        "pt1s",
        "PT1S\n",
    ],
)
def test_unknown_duration(value):
    with pytest.raises(DurationParseError):
        parse_iso8601_duration(value)
    assert duration_seconds_or_none(value) is None


def test_missing_duration():
    assert duration_seconds_or_none(None) is None


@pytest.mark.parametrize(
    "ts", ["2026-11-23T00:00:00.5Z", "2026-11-23T05:30:00.5+05:30", "2026-11-22T23:00:00.500-01:00"]
)
def test_timestamp(ts):
    parsed = parse_rfc3339_utc(ts)
    assert parsed.tzinfo is UTC and format_utc(parsed) == "2026-11-23T00:00:00.500000Z"


@pytest.mark.parametrize(
    "ts",
    [
        "2026-11-23",
        "2026-11-23T00:00:00",
        "2026-13-23T00:00:00Z",
        "2026-11-23T00:00:00+00:60",
        "2026-11-23 00:00:00Z",
    ],
)
def test_invalid_timestamp(ts):
    with pytest.raises(ValueError):
        parse_rfc3339_utc(ts)


def test_naive_format():
    with pytest.raises(ValueError):
        format_utc(datetime(2026, 11, 23))
