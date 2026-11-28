"""Project the shared loader's account models onto the FR-4 metric catalogue."""

from collections.abc import Sequence

from yt_intel.account.loader import AccountSignalsLoader
from yt_intel.account.types import SignalKind
from yt_intel.analytics.engine import Observation, Source
from yt_intel.common import AppError, ErrorCode, Principal

from .engagement import Coverage, LoadedSignals


class AccountSignalAdapter:
    def __init__(self, loader: AccountSignalsLoader) -> None:
        self.loader = loader

    async def load(
        self,
        principal: Principal,
        want: frozenset[Source],
        *,
        playlist_ids: Sequence[str] = (),
        like_cap: int = 1000,
    ) -> dict[Source, LoadedSignals]:
        (source,) = want
        signals = await self.loader.load(
            principal, frozenset({SignalKind(source)}), playlist_ids=playlist_ids, like_cap=like_cap
        )
        if source == "liked_videos" and signals.liked_videos is not None:
            coverage = signals.liked_videos.coverage
            rows = [
                Observation(
                    v.video_published_at,
                    v.video_id,
                    v.channel_id,
                    v.category_id,
                    duration_seconds=v.duration_seconds,
                )
                for v in signals.liked_videos.items
            ]
        elif source == "subscriptions" and signals.subscriptions is not None:
            coverage = signals.subscriptions.coverage
            rows = [
                Observation(s.subscription_created_at, channel_id=s.channel_id)
                for s in signals.subscriptions.items
            ]
        elif (
            source == "playlist_items"
            and signals.playlist_items
            and playlist_ids
            and playlist_ids[0] in signals.playlist_items
        ):
            page = signals.playlist_items[playlist_ids[0]]
            coverage = page.coverage
            rows = [Observation(i.playlist_item_added_at, video_id=i.video_id) for i in page.items]
        else:
            raise AppError(ErrorCode.UPSTREAM_ERROR, "Requested account signal set is unavailable")
        return {
            source: LoadedSignals(
                items=rows, coverage=Coverage.model_validate(coverage, from_attributes=True)
            )
        }
