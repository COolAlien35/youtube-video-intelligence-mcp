"""Unit tests for FixtureAccountProvider."""

from __future__ import annotations

import pytest

from yt_intel.common.errors import AppError, ErrorCode
from yt_intel.common.types import Principal
from yt_intel.provider.account_fixture import FixtureAccountProvider

_CHAN_A = "UC1234567890123456789012"
_CHAN_B = "UC9999999999999999999999"


def _make_like(vid: str, channel_id: str) -> dict[str, object]:
    return {
        "id": vid,
        "snippet": {
            "channelId": channel_id,
            "title": f"Video {vid}",
            "publishedAt": "2026-11-20T00:00:00Z",
        },
        "contentDetails": {"duration": "PT2M"},
    }


async def test_fixture_account_provider_paging_isolation_and_call_counter() -> None:
    p1 = Principal(issuer="https://issuer.example", subject="alice")
    p2 = Principal(issuer="https://issuer.example", subject="bob")
    raw_sets = {
        "set_a": {
            "likes": {
                "items": [
                    _make_like("vid00000001", _CHAN_A),
                    _make_like("vid00000002", _CHAN_A),
                    _make_like("vid00000003", _CHAN_A),
                ]
            },
            "subscriptions": {
                "items": [
                    {
                        "id": "sub-a",
                        "snippet": {
                            "title": "Chan A",
                            "publishedAt": "2026-10-01T00:00:00Z",
                            "resourceId": {"channelId": _CHAN_A},
                        },
                    }
                ]
            },
        },
        "set_b": {
            "likes": {"items": [_make_like("vid00000099", _CHAN_B)]},
        },
    }
    provider = FixtureAccountProvider({p1.key: "set_a", p2.key: "set_b"}, raw_sets=raw_sets)

    page1 = await provider.list_liked_videos(p1, page_size=2)
    assert [v.video_id for v in page1.items] == ["vid00000001", "vid00000002"]
    assert page1.next_page_token == "offset:2"  # noqa: S105
    assert page1.reported_total == 3

    page2 = await provider.list_liked_videos(p1, page_token=page1.next_page_token, page_size=2)
    assert [v.video_id for v in page2.items] == ["vid00000003"]
    assert page2.next_page_token is None

    other = await provider.list_liked_videos(p2, page_size=10)
    assert [v.video_id for v in other.items] == ["vid00000099"]
    assert provider.calls["list_liked_videos"] == 3

    subs = await provider.list_subscriptions(p1)
    assert len(subs.items) == 1
    assert provider.calls["list_subscriptions"] == 1


async def test_fixture_account_provider_rejects_unknown_principal_and_bad_token() -> None:
    p1 = Principal(issuer="https://issuer.example", subject="alice")
    unknown = Principal(issuer="https://issuer.example", subject="stranger")
    provider = FixtureAccountProvider(
        {p1.key: "set_a"},
        raw_sets={"set_a": {"likes": {"items": []}}},
    )
    with pytest.raises(AppError) as exc:
        await provider.list_liked_videos(unknown)
    assert exc.value.code is ErrorCode.AUTH_REQUIRED

    with pytest.raises(AppError) as exc2:
        await provider.list_liked_videos(p1, page_token="bad-token")  # noqa: S106
    assert exc2.value.code is ErrorCode.INVALID_INPUT
