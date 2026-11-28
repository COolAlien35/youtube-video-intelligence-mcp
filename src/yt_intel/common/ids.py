"""Resolve supported YouTube references locally, without provider discovery."""

import re
import unicodedata
from dataclasses import dataclass
from typing import Literal
from urllib.parse import parse_qs, unquote, urlsplit

from .errors import AppError, ErrorCode

_VIDEO = re.compile(r"[a-zA-Z0-9_-]{11}")
_CHANNEL = re.compile(r"UC[a-zA-Z0-9_-]{22}")
_PLAYLIST = re.compile(r"[a-zA-Z0-9_-]+")
_SEPARATORS = frozenset("_.·-")
_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com"}
_SHORT = {"youtu.be", "www.youtu.be"}


@dataclass(frozen=True)
class ChannelRef:
    kind: Literal["id", "handle", "username"]
    value: str


def _invalid(reason: str) -> AppError:
    return AppError(ErrorCode.INVALID_INPUT, reason)


def _parts(value: str) -> tuple[str, str, dict[str, list[str]]]:
    if not isinstance(value, str) or any(c.isspace() or ord(c) < 32 for c in value):
        raise _invalid("Expected a YouTube URL without whitespace")
    try:
        parts = urlsplit(value if "://" in value else "https://" + value)
    except ValueError as exc:
        raise _invalid("Malformed YouTube URL") from exc
    host = parts.netloc.lower()
    if parts.scheme not in {"http", "https"} or host not in _HOSTS | _SHORT:
        raise _invalid("Expected a supported YouTube host")
    return (
        host,
        unquote(parts.path, errors="replace"),
        parse_qs(parts.query, keep_blank_values=True),
    )


def _single(query: dict[str, list[str]], key: str) -> str:
    values = query.get(key, [])
    if len(values) != 1:
        raise _invalid(f"Expected a single {key} parameter")
    return values[0]


def parse_video_id(value: str) -> str:
    if isinstance(value, str) and _VIDEO.fullmatch(value):
        return value
    host, path, query = _parts(value)
    if host in _SHORT:
        candidate = path.removeprefix("/")
    elif path == "/watch":
        candidate = _single(query, "v")
    else:
        match = re.fullmatch(r"/(?:shorts|embed|live)/([^/]+)", path)
        if not match:
            raise _invalid("Unsupported video URL path")
        candidate = match[1]
    if not _VIDEO.fullmatch(candidate):
        raise _invalid("Expected an 11-character video ID")
    return candidate


def parse_playlist_id(value: str) -> str:
    if isinstance(value, str) and _PLAYLIST.fullmatch(value):
        return value
    _, _, query = _parts(value)
    candidate = _single(query, "list")
    if not _PLAYLIST.fullmatch(candidate):
        raise _invalid("Playlist ID is empty or contains unsupported characters")
    return candidate


def parse_channel_ref(value: str) -> ChannelRef:
    if isinstance(value, str) and _CHANNEL.fullmatch(value):
        return ChannelRef("id", value)
    if isinstance(value, str) and value.startswith("@"):
        handle = value[1:]
    else:
        host, path, _ = _parts(value)
        if host not in _HOSTS or re.search(r"%2f|%5c", value, re.IGNORECASE):
            raise _invalid("Expected a YouTube channel URL")
        segments = path.strip("/").split("/")
        if segments[0] in {"user", "c"}:
            raise _invalid("Legacy URL unsupported. Supply the channel ID or @handle")
        if segments[0] == "channel" and len(segments) >= 2 and _CHANNEL.fullmatch(segments[1]):
            return ChannelRef("id", segments[1])
        if not segments[0].startswith("@"):
            raise _invalid("Expected an exact channel ID or @handle")
        handle = segments[0][1:]

    handle = unicodedata.normalize("NFC", handle)
    names = [unicodedata.name(char, "") for char in handle if char.isalpha()]
    if names and all(name.startswith(("CJK", "HANGUL", "IDEOGRAPHIC")) for name in names):
        minimum, maximum = 1, 10
    elif names and all(name.startswith(("HIRAGANA", "KATAKANA", "ETHIOPIC")) for name in names):
        minimum, maximum = 2, 20
    else:
        minimum, maximum = 3, 30
    if (
        not minimum <= len(handle) <= maximum
        or handle[0] in _SEPARATORS
        or handle[-1] in _SEPARATORS
        or not all(
            char.isalnum() or unicodedata.category(char).startswith("M") or char in _SEPARATORS
            for char in handle
        )
    ):
        raise _invalid("Malformed channel handle")
    return ChannelRef("handle", "@" + handle)
