import json
import re
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.security

CREDENTIAL = re.compile(r"AIza[\w-]{30,}|ya29\.[\w.-]+|eyJ[\w-]+\.[\w-]+\.[\w-]+")
EMAIL = re.compile(r"[\w.+-]+@([\w.-]+)")
ID_PATTERNS = {
    "videoId": r"SYNV_[\w-]{6}",
    "channelId": r"UCSYN[\w-]{19}",
    "playlistId": r"PLSYN[\w-]+",
    "customUrl": r"@syn_[\w-]+",
}


def inspect_value(value: Any, key: str, resource: str) -> None:
    if isinstance(value, dict):
        for name, field in value.items():
            inspect_value(field, name, resource)
    elif isinstance(value, list):
        for field in value:
            inspect_value(field, key, resource)
    elif isinstance(value, str):
        assert not CREDENTIAL.search(value)
        assert all(domain == "example.invalid" for domain in EMAIL.findall(value))
        if any(
            term in key.lower() for term in ("token", "secret", "password", "apikey", "api_key")
        ):
            assert value.startswith("FAKE_")
        pattern = ID_PATTERNS.get(key)
        if key == "id":
            if resource.startswith("videos.list") or resource == "likes":
                pattern = ID_PATTERNS["videoId"]
            elif resource in {"channel", "channels.list"}:
                pattern = ID_PATTERNS["channelId"]
            elif resource == "playlists":
                pattern = ID_PATTERNS["playlistId"]
            else:
                pattern = r"SYNITEM_[\w-]+"
        if pattern:
            assert re.fullmatch(pattern, value), f"Invalid synthetic {key}"


def test_fixture_tree(fixtures_dir: Path) -> None:
    files = sorted(fixtures_dir.parent.rglob("*.json"))
    assert files
    for path in files:
        try:
            inspect_value(json.loads(path.read_text(encoding="utf8")), "", path.stem)
        except AssertionError as exc:
            raise AssertionError(f"Fixture safety check failed in {path.name}") from exc
