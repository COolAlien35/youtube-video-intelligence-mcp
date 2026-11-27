from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from yt_intel.common.clock import FakeClock
from yt_intel.provider.fixture import FixtureProvider

ROOT = Path(__file__).resolve().parent


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        path = item.path.relative_to(ROOT)
        if path.as_posix() in {"test_smoke.py", "test_validate_traceability.py"}:
            continue
        if len(path.parts) < 2 or path.parts[0] not in {"unit", "integration", "e2e"}:
            raise pytest.UsageError(f"Unclassified test {path}: use unit, integration or e2e")
        item.add_marker(getattr(pytest.mark, path.parts[0]))


@pytest.fixture
def fixtures_dir() -> Path:
    return ROOT / "fixtures/youtube"


@pytest.fixture
def fixture_provider(fixtures_dir: Path) -> FixtureProvider:
    return FixtureProvider(fixtures_dir)


@pytest.fixture
def frozen_clock() -> FakeClock:
    return FakeClock(datetime(2026, 1, 1, tzinfo=UTC))


@pytest.fixture
def settings_factory() -> Any:
    from yt_intel.config import Settings

    def make(**overrides: Any) -> Settings:
        return Settings(**({"_env_file": None, "environment": "test"} | overrides))

    return make
