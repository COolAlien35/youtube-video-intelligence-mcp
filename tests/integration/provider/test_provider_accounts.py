import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest

from yt_intel.common.errors import AppError, ErrorCode
from yt_intel.provider.factory import build_provider
from yt_intel.provider.fixture import FaultPlan, FixtureProvider
from yt_intel.provider.models import AccountRef

pytestmark = pytest.mark.integration


def test_factory_gate() -> None:
    with pytest.raises(AppError) as error:
        build_provider(SimpleNamespace(live_youtube_enabled=True, fixtures_dir=None))
    assert error.value.code == ErrorCode.POLICY_GATE_CLOSED
    assert isinstance(
        build_provider(SimpleNamespace(live_youtube_enabled=False, fixtures_dir=None)),
        FixtureProvider,
    )


def test_account_reads_and_writes() -> None:
    async def scenario() -> None:
        root = Path(__file__).resolve().parents[2] / "fixtures/youtube"
        provider = FixtureProvider(root, FaultPlan("insert_playlist_item", 2))
        alpha, beta = AccountRef("user_alpha"), AccountRef("user_beta")
        assert len(await provider.list_liked_videos(alpha)) == 50
        assert len(await provider.list_subscriptions(alpha)) == 12
        assert len(await provider.list_playlists(alpha)) == 4
        assert len(await provider.list_playlist_items(alpha, "PLSYN_user_alpha_0")) == 3
        pid = await provider.create_playlist(alpha, "Test", "", "private")
        await provider.insert_playlist_item(alpha, pid, "SYNV_000001")
        with pytest.raises(AppError) as error:
            await provider.insert_playlist_item(alpha, pid, "SYNV_000002")
        assert error.value.code == ErrorCode.UPSTREAM_ERROR
        assert len(await provider.list_playlist_items(alpha, pid)) == 1
        with pytest.raises(AppError) as error:
            await provider.list_playlist_items(beta, pid)
        assert error.value.code == ErrorCode.NOT_FOUND_OR_UNAVAILABLE
        with pytest.raises(AppError) as error:
            await provider.create_playlist(AccountRef("user_nochannel"), "Test", "", "private")
        assert error.value.code == ErrorCode.CHANNEL_REQUIRED
        assert len(await FixtureProvider(root).list_playlists(alpha)) == 4

    asyncio.run(scenario())
