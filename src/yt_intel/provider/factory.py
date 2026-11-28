from pathlib import Path
from typing import Protocol

from yt_intel.common.errors import AppError, ErrorCode, PolicyGateClosedError
from yt_intel.policy.gates import PolicyGates

from .base import YouTubeProvider
from .fixture import FixtureProvider


class ProviderSettings(Protocol):
    @property
    def fixtures_dir(self) -> Path | None: ...
    @property
    def live_youtube_enabled(self) -> bool: ...


def build_provider(
    settings: ProviderSettings, *, gates: PolicyGates | None = None
) -> YouTubeProvider:
    if settings.live_youtube_enabled:
        policy = gates or PolicyGates.from_settings(settings)
        if not policy.live_youtube_allowed():
            raise PolicyGateClosedError()
        raise AppError(ErrorCode.NOT_IMPLEMENTED, "Live provider is unavailable in Phase 3")
    default = Path(__file__).resolve().parents[3] / "tests/fixtures/youtube"
    return FixtureProvider(settings.fixtures_dir or default)
