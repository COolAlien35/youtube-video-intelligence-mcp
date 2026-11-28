"""Seed lookup within a caller's active quota reservation."""

from yt_intel.common import AppError, ErrorCode
from yt_intel.provider.base import YouTubeProvider
from yt_intel.provider.models import VideoMetadata


async def resolve_seed(provider: YouTubeProvider, canonical_id: str) -> VideoMetadata:
    batch = await provider.get_videos([canonical_id])
    if canonical_id not in batch.unavailable_ids:
        for item in batch.videos:
            if item.id == canonical_id:
                return item
    raise AppError(ErrorCode.NOT_FOUND_OR_UNAVAILABLE, "Seed video unavailable")
