"""Write-path provider protocol, result types, and fault-injection contracts (Phase 6)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, Protocol, runtime_checkable

from yt_intel.common.errors import AppError, ErrorCode

if TYPE_CHECKING:
    from datetime import datetime

    from yt_intel.common.types import Principal

# Official YouTube Data API v3 scope required for playlists.insert & playlistItems.insert
YOUTUBE_WRITE_SCOPE = "https://www.googleapis.com/auth/youtube"

FaultKind = Literal[
    "timeout_after_success",
    "timeout_before_effect",
    "permanent_error",
    "signup_required",
    "quota_exceeded",
    "invalid_grant",
]


@dataclass(frozen=True)
class Fault:
    """Fault-injection specification for FixtureWritePlaylistProvider."""

    op: Literal["get_my_channel", "create_playlist", "insert_playlist_item", "find_playlists"]
    at: int = 1  # 1-based call index for *op* (0 = always)
    kind: FaultKind = "permanent_error"


@dataclass(frozen=True)
class ChannelInfo:
    """Authenticated user's YouTube channel metadata."""

    channel_id: str
    title: str | None = None


@dataclass(frozen=True)
class CreatedPlaylist:
    """Result of ``playlists.insert``."""

    playlist_id: str
    title: str
    privacy: str
    created_at: datetime


@dataclass(frozen=True)
class CreatedItem:
    """Result of ``playlistItems.insert``."""

    playlist_item_id: str
    playlist_id: str
    video_id: str
    position: int


@dataclass(frozen=True)
class PlaylistSummaryInfo:
    """Remote playlist summary returned by ``find_playlists`` for reconciliation."""

    playlist_id: str
    title: str
    description: str
    privacy: str
    created_at: datetime


@dataclass(frozen=True)
class RemotePlaylistItem:
    """Remote playlist item returned by ``list_playlist_items`` for reconciliation."""

    playlist_item_id: str
    video_id: str
    position: int


class ChannelRequiredError(AppError):
    """Recoverable error raised when no YouTube channel exists or youtubeSignupRequired occurs."""

    def __init__(self, message: str | None = None) -> None:
        super().__init__(
            ErrorCode.CHANNEL_REQUIRED,
            message
            or "A YouTube channel is required for this Google account before creating playlists.",
            retryable=False,
        )


class WriteScopeRequiredError(AppError):
    """Raised when the connected Google grant lacks the YouTube write scope."""

    def __init__(self, message: str | None = None) -> None:
        super().__init__(
            ErrorCode.FORBIDDEN,
            message
            or "YouTube write permission is required. Re-authorize with incremental write consent.",
            details={"required_scope": YOUTUBE_WRITE_SCOPE},
            retryable=False,
        )


@runtime_checkable
class PlaylistWriteProvider(Protocol):
    """Protocol for playlist write operations. Implementations must NEVER retry writes."""

    async def get_my_channel(self, principal: Principal) -> ChannelInfo:
        """Return the principal's YouTube channel or raise ChannelRequiredError."""
        ...

    async def create_playlist(
        self,
        principal: Principal,
        *,
        title: str,
        description: str,
        privacy: str,
    ) -> CreatedPlaylist:
        """Create a playlist (playlists.insert, 50 units)."""
        ...

    async def insert_playlist_item(
        self,
        principal: Principal,
        *,
        playlist_id: str,
        video_id: str,
        position: int,
    ) -> CreatedItem:
        """Insert a video at *position* (playlistItems.insert, 50 units)."""
        ...

    async def find_playlists(
        self,
        principal: Principal,
        *,
        title: str,
        created_after: datetime,
    ) -> tuple[PlaylistSummaryInfo, ...]:
        """List owned playlists matching *title* created at or after *created_after*."""
        ...

    async def list_playlist_items(
        self,
        principal: Principal,
        playlist_id: str,
    ) -> tuple[RemotePlaylistItem, ...]:
        """List all items currently in *playlist_id* for reconciliation."""
        ...
