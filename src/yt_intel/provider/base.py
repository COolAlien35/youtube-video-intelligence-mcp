from collections.abc import Sequence
from typing import Protocol

from yt_intel.common.ids import ChannelRef

from .models import (
    AccountRef,
    Channel,
    ChannelBatch,
    PlaylistItem,
    PlaylistSummary,
    SearchPage,
    Subscription,
    VideoBatch,
    VideoMetadata,
)


class YouTubeProvider(Protocol):
    """Callers reserve quota before I/O. Every method may raise a mapped upstream
    error; account operations additionally require valid principal authorization.
    """

    async def get_videos(self, video_ids: Sequence[str]) -> VideoBatch:
        """Return available videos in requested order and identify absent IDs."""
        ...

    async def search_videos(
        self, query: str, *, max_results: int = 50, page_token: str | None = None
    ) -> SearchPage:
        """Page through video references. Invalid cursors raise INVALID_INPUT."""
        ...

    async def get_channels(self, channel_ids: Sequence[str]) -> ChannelBatch:
        """Return channels in requested order and identify absent IDs."""
        ...

    async def resolve_channel(self, ref: ChannelRef) -> Channel | None:
        """Resolve an exact ID, handle or username, returning None for an unknown reference."""
        ...

    async def list_liked_videos(
        self, account: AccountRef, *, limit: int = 1000
    ) -> list[VideoMetadata]:
        """Return at most 1,000 accessible likes for this principal."""
        ...

    async def list_subscriptions(self, account: AccountRef) -> list[Subscription]:
        """Read account subscriptions with their creation times."""
        ...

    async def list_playlists(self, account: AccountRef) -> list[PlaylistSummary]:
        """Read only playlists accessible to this account."""
        ...

    async def list_playlist_items(
        self, account: AccountRef, playlist_id: str
    ) -> list[PlaylistItem]:
        """Return ordered items; unavailable playlists raise NOT_FOUND_OR_UNAVAILABLE."""
        ...

    async def get_own_channel(self, account: AccountRef) -> Channel:
        """Resolve the account channel or raise CHANNEL_REQUIRED."""
        ...

    async def create_playlist(
        self, account: AccountRef, title: str, description: str, visibility: str
    ) -> str:
        """Create a playlist for an eligible account and return its ID."""
        ...

    async def insert_playlist_item(
        self, account: AccountRef, playlist_id: str, video_id: str
    ) -> str:
        """Insert an available video into an owned playlist and return the item ID."""
        ...
