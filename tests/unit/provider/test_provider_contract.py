import asyncio
import json
from pathlib import Path

import pytest

from yt_intel.common.ids import parse_channel_ref
from yt_intel.provider.base import YouTubeProvider
from yt_intel.provider.fixture import FixtureProvider
from yt_intel.provider.models import AccountRef


@pytest.fixture(params=["fixture_provider"])
def adapter(request: pytest.FixtureRequest) -> YouTubeProvider:
    return request.getfixturevalue(request.param)


def test_batch_and_exact_resolution(adapter: YouTubeProvider) -> None:
    async def run() -> None:
        requested = ["SYNV_000003", "SYNV_absent", "SYNV_000002"]
        batch = await adapter.get_videos(requested)
        assert [v.id for v in batch.videos] == [requested[0], requested[2]]
        assert batch.unavailable_ids == (requested[1],)
        assert [v.duration_seconds for v in batch.videos] == [None, 0]
        channel = await adapter.resolve_channel(parse_channel_ref("@syn_studio_0"))
        assert channel and channel.handle == "@syn_studio_0"
        assert await adapter.resolve_channel(parse_channel_ref("@Studio")) is None
        channels = await adapter.get_channels(["missing", channel.id])
        assert channels.channels == (channel,) and channels.unavailable_ids == ("missing",)

    asyncio.run(run())


def test_paging_and_limit(adapter: YouTubeProvider) -> None:
    async def run() -> None:
        first = await adapter.search_videos("async programming")
        assert len(first.video_ids) == 50 and first.next_page_token
        second = await adapter.search_videos("async programming", page_token=first.next_page_token)
        assert len(second.video_ids) == 50 and second.next_page_token is None
        assert first.video_ids[0] in second.video_ids
        assert len((await adapter.search_videos("async programming", max_results=3)).video_ids) == 3
        account = AccountRef("user_alpha")
        assert len(await adapter.list_liked_videos(account, limit=4)) == 4
        assert await adapter.list_liked_videos(account, limit=0) == []

    asyncio.run(run())


def test_like_ceiling(tmp_path: Path, fixtures_dir: Path) -> None:
    import shutil

    root = tmp_path / "catalogue"
    shutil.copytree(fixtures_dir, root)
    likes = root / "user_alpha/likes.json"
    raw = json.loads(likes.read_text())
    raw["items"] *= 21
    likes.write_text(json.dumps(raw))
    provider = FixtureProvider(root)
    assert (
        len(asyncio.run(provider.list_liked_videos(AccountRef("user_alpha"), limit=2000))) == 1000
    )
