import pytest

from yt_intel.provider.error_mapping import map_api_error
from yt_intel.provider.normalize import video

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("status", "reason", "expected"),
    [
        (400, "invalidParameter", "INVALID_INPUT"),
        (404, "videoNotFound", "NOT_FOUND_OR_UNAVAILABLE"),
        (403, "quotaExceeded", "QUOTA_EXCEEDED"),
        (403, "rateLimitExceeded", "RATE_LIMITED"),
        (403, "forbidden", "FORBIDDEN"),
        (400, "invalid_grant", "AUTH_EXPIRED_OR_REVOKED"),
        (401, "youtubeSignupRequired", "CHANNEL_REQUIRED"),
        (500, "backendError", "UPSTREAM_ERROR"),
    ],
)
def test_reason_precedence(status: int, reason: str, expected: str) -> None:
    assert map_api_error(status, reason).code.value == expected


@pytest.mark.parametrize(
    ("raw", "seconds"), [(None, None), ("invalid", None), ("P0D", 0), ("PT1M", 60)]
)
def test_optional_metadata(raw: str | None, seconds: int | None) -> None:
    item = video(
        {
            "id": "SYNV_000001",
            "snippet": {
                "title": "",
                "description": "",
                "channelId": "UCSYN0000000000000000000",
                "publishedAt": "2026-01-01T00:00:00Z",
            },
            "contentDetails": {"duration": raw},
        }
    )
    assert item.duration_seconds == seconds
    assert item.tags is None and item.default_audio_language is None
    assert item.published_at.utcoffset() is not None
