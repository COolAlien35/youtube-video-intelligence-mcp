from pathlib import Path
from typing import Protocol

from yt_intel.common.errors import AppError, ErrorCode

from .base import YouTubeProvider
from .fixture import FixtureProvider


class ProviderSettings(Protocol):
    @property
    def fixtures_dir(self) -> Path | None: ...
    @property
    def live_youtube_enabled(self) -> bool: ...


def build_provider(settings: ProviderSettings) -> YouTubeProvider:
    if settings.live_youtube_enabled:
        raise AppError(ErrorCode.POLICY_GATE_CLOSED, "Live YouTube provider is gated")
    default = Path(__file__).resolve().parents[3] / "tests/fixtures/youtube"
    return FixtureProvider(settings.fixtures_dir or default)
