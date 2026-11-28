import pytest

from yt_intel.common.errors import AppError, ErrorCode
from yt_intel.common.ids import parse_channel_ref

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("handle", ["@星", "@かな", "@한", "@Studio·Lab", "@café"])
def test_bare_and_channel_tab_agree(handle):
    expected = parse_channel_ref(handle)
    assert expected.value == handle
    assert parse_channel_ref(f"https://m.youtube.com/{handle}/videos?view=0") == expected


@pytest.mark.parametrize(
    "ref",
    [
        "@.abc",
        "@foo-",
        "@ab",
        "@" + "a" * 31,
        "@foo/videos",
        "youtube.com/c/Studio",
        "youtube.com/user/Studio",
        "youtube.com/@foo%2Fvideos",
        "UC" + "a" * 21,
    ],
)
def test_invalid_before_lookup(ref):
    with pytest.raises(AppError) as error:
        parse_channel_ref(ref)
    assert error.value.code == ErrorCode.INVALID_INPUT
