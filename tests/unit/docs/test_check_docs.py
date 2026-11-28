"""Tests for scripts/check_docs.py."""

from pathlib import Path

import pytest

from scripts.check_docs import check_docs, registry_tool_names, settings_env_vars

pytestmark = [pytest.mark.unit]


def _seed_minimal_repo(tmp_path: Path) -> Path:
    (tmp_path / "src/yt_intel/tools").mkdir(parents=True)
    (tmp_path / "src/yt_intel/config").mkdir(parents=True)
    (tmp_path / "src/yt_intel/tools/registry.py").write_text(
        "TOOLS = (similar_videos,)\n", encoding="utf8"
    )
    (tmp_path / "src/yt_intel/config/settings.py").write_text(
        "class Settings:\n    live_youtube_enabled: bool = False\n", encoding="utf8"
    )
    return tmp_path


def test_repo_docs_pass() -> None:
    assert "similar_videos" in registry_tool_names()
    assert "YT_INTEL_LIVE_YOUTUBE_ENABLED" in settings_env_vars()
    assert check_docs() == []


def test_catches_broken_link(tmp_path: Path) -> None:
    repo = _seed_minimal_repo(tmp_path)
    (repo / "README.md").write_text("See [missing](docs/nope.md).\n", encoding="utf8")
    errors = check_docs(repo)
    assert any("broken link" in err for err in errors)


def test_catches_unknown_env_var(tmp_path: Path) -> None:
    repo = _seed_minimal_repo(tmp_path)
    (repo / "README.md").write_text("Set `YT_INTEL_DOES_NOT_EXIST=1`.\n", encoding="utf8")
    errors = check_docs(repo)
    assert any("unknown setting 'YT_INTEL_DOES_NOT_EXIST'" in err for err in errors)


def test_catches_stray_tbc_or_todo(tmp_path: Path) -> None:
    repo = _seed_minimal_repo(tmp_path)
    (repo / "README.md").write_text("Pending decision: TBC.\n", encoding="utf8")
    errors = check_docs(repo)
    assert any("unresolved marker 'TBC'" in err for err in errors)
