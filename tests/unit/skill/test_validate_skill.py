import shutil

import pytest

from scripts.validate_skill import ROOT, SKILL, validate


def test_package():
    validate()


@pytest.mark.parametrize(
    "old,new",
    [
        ("Resolve the seed", "Execute"),
        ("name: video-to-playlist", "name: x"),
        ("Stop without further writes", "Continue"),
        ("`similar_videos`", "`new_tool`"),
        ("Report the outcome", "Skip confirmation"),
    ],
)
def test_rejects(tmp_path, old, new):
    for p in (SKILL, "src/yt_intel/tools/registry.py"):
        target = tmp_path / p
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / p, target)
    target = tmp_path / SKILL
    target.write_text(target.read_text().replace(old, new))
    with pytest.raises(ValueError):
        validate(tmp_path)
