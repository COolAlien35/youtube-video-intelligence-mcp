"""Resolve supported YouTube references locally, without provider discovery."""

import re
from dataclasses import dataclass
from typing import Literal
from urllib.parse import parse_qs, unquote, urlsplit

from .errors import AppError, ErrorCode

_VIDEO = re.compile(r"[a-zA-Z0-9_-]{11}")
_CHANNEL = re.compile(r"UC[a-zA-Z0-9_-]{22}")
_PLAYLIST = re.compile(r"[a-zA-Z0-9_-]+")
_NAME = re.compile(r"[\w.·-]+")
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
        path = "/" + value
    else:
        host, path, _ = _parts(value)
        if host not in _HOSTS:
            raise _invalid("Expected a YouTube channel URL")
    path = path.removesuffix("/")
    if path.startswith("/@") and _NAME.fullmatch(path[2:]):
        return ChannelRef("handle", path[1:])
    if path.startswith("/channel/") and _CHANNEL.fullmatch(path[9:]):
        return ChannelRef("id", path[9:])
    if path.startswith("/user/") and _NAME.fullmatch(path[6:]):
        return ChannelRef("username", path[6:])
    raise _invalid("Expected an exact channel ID, handle or legacy username")
