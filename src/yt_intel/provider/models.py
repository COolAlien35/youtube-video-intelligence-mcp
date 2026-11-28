from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class AccountRef:
    principal_key: str


@dataclass(frozen=True)
class VideoMetadata:
    id: str
    channel_id: str
    title: str
    description: str
    published_at: datetime
    duration_seconds: int | None
    tags: tuple[str, ...] | None
    default_audio_language: str | None
    category_id: str | None
    view_count: int | None


@dataclass(frozen=True)
class Channel:
    id: str
    title: str
    description: str
    handle: str | None
    username: str | None = None
    keywords: tuple[str, ...] = ()


@dataclass(frozen=True)
class VideoBatch:
    videos: tuple[VideoMetadata, ...]
    unavailable_ids: tuple[str, ...]


@dataclass(frozen=True)
class ChannelBatch:
    channels: tuple[Channel, ...]
    unavailable_ids: tuple[str, ...]


@dataclass(frozen=True)
class SearchPage:
    video_ids: tuple[str, ...]
    next_page_token: str | None


@dataclass(frozen=True)
class Subscription:
    channel_id: str
    subscription_created_at: datetime


@dataclass(frozen=True)
class PlaylistSummary:
    id: str
    title: str
    description: str
    visibility: str


@dataclass(frozen=True)
class PlaylistItem:
    id: str
    playlist_id: str
    video_id: str
    position: int
    playlist_item_added_at: datetime | None


@dataclass(frozen=True)
class ChannelSearchPage:
    channel_ids: tuple[str, ...]
    next_page_token: str | None
