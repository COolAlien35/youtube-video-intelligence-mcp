import pytest

from yt_intel.common import AppError, ErrorCode
from yt_intel.common.ids import parse_video_id
from yt_intel.services.video_seed import resolve_seed

SEED = "SYNV_000000"


@pytest.mark.parametrize(
    "ref",
    [
        SEED,
        f"https://www.youtube.com/watch?v={SEED}",
        f"https://youtu.be/{SEED}",
        f"https://youtube.com/shorts/{SEED}",
    ],
)
async def test_variants_resolve_exact_seed(fixture_provider, ref):
    assert (await resolve_seed(fixture_provider, parse_video_id(ref))).id == SEED


async def test_invalid_and_absent(fixture_provider):
    with pytest.raises(AppError) as invalid:
        await resolve_seed(fixture_provider, parse_video_id("bad"))
    assert invalid.value.code == ErrorCode.INVALID_INPUT and not fixture_provider.calls
    with pytest.raises(AppError) as missing:
        await resolve_seed(fixture_provider, parse_video_id("SYNV_absent"))
    assert missing.value.code == ErrorCode.NOT_FOUND_OR_UNAVAILABLE
    assert fixture_provider.calls == {"get_videos": 1}
