"""Offline account loader for the fixture deployment until A's shared loader lands."""

from collections.abc import Sequence
from contextlib import ExitStack
from datetime import UTC, datetime, timedelta

from sqlalchemy.engine import Engine

from yt_intel.analytics.engine import Observation, Source
from yt_intel.cache.store import CacheStore
from yt_intel.common import AppError, ErrorCode, Principal
from yt_intel.config import Settings
from yt_intel.google_oauth.client import READ
from yt_intel.google_oauth.fake import FakeGoogleOAuth
from yt_intel.provider.base import YouTubeProvider
from yt_intel.provider.models import AccountRef
from yt_intel.quota import QuotaPlan, QuotaPlanner, batched_lookup_units
from yt_intel.security.crypto import EncryptedBlob, decrypt_token
from yt_intel.server.oauth_routes import GoogleLink
from yt_intel.storage import session_scope
from yt_intel.storage.grants import GrantRepo
from yt_intel.storage.scoped import ScopedSession

from .engagement import DETAIL_CAP, LABELS, Coverage, LoadedSignals

SIGNAL_KIND = "engagement_signals"


def reconnect(reason: str) -> AppError:
    return AppError(
        ErrorCode.AUTH_EXPIRED_OR_REVOKED,
        "Reconnect the Google account",
        details={"reason": reason},
    )


class FixtureSignalsLoader:
    def __init__(
        self,
        engine: Engine,
        link: GoogleLink | None,
        provider: YouTubeProvider,
        planner: QuotaPlanner,
        settings: Settings,
    ) -> None:
        self.settings = settings
        self.engine = engine
        self.link = link
        self.provider = provider
        self.planner = planner

    async def _account(self, principal: Principal) -> str:
        with session_scope(self.engine) as session:
            grant = GrantRepo(ScopedSession(session, principal)).get(principal)
            if not grant or grant.status != "active":
                raise reconnect("not_connected")
            if READ not in grant.granted_scopes.split():
                raise reconnect("insufficient_scope")
            if not self.link or not isinstance(self.link.google, FakeGoogleOAuth):
                raise AppError(ErrorCode.POLICY_GATE_CLOSED, "Live account access is disabled")
            if not grant.nonce or not grant.ciphertext or grant.key_version is None:
                raise reconnect("invalid_grant")
            refresh = decrypt_token(
                EncryptedBlob(grant.key_version, grant.nonce, grant.ciphertext),
                principal=principal,
                keyring=self.link.ring,
            )
            account = grant.account_ref
        try:
            tokens = await self.link.google.refresh(refresh)
            subject = await self.link.google.subject(tokens.access_token)
        except AppError:
            raise reconnect("invalid_grant") from None
        if READ not in tokens.scopes or subject != account:
            raise reconnect("insufficient_scope")
        return account

    async def load(
        self,
        principal: Principal,
        want: frozenset[Source],
        *,
        playlist_ids: Sequence[str] = (),
        like_cap: int = 1000,
    ) -> dict[Source, LoadedSignals]:
        account = await self._account(principal)
        (source,) = want
        playlist = playlist_ids[0] if playlist_ids else ""
        key = f"{account}/{source}/{playlist}"
        with session_scope(self.engine) as session:
            hit = CacheStore(ScopedSession(session, principal)).get(SIGNAL_KIND, key)
        if hit:
            signals = LoadedSignals.model_validate(hit.value)
            signals.coverage.from_cache = True
            return {source: signals}
        cap = {
            "liked_videos": min(like_cap, 1000, self.settings.account_like_cap),
            "subscriptions": self.settings.account_subscription_cap,
            "playlist_items": self.settings.account_playlist_items_cap,
        }[source]
        with ExitStack() as holds:
            detail_hold = None
            if source == "playlist_items":
                detail_hold = self.planner.reserve(
                    principal, QuotaPlan(batched_lookup_units(DETAIL_CAP))
                )
                holds.callback(detail_hold.release)
            reservation = self.planner.reserve(principal, QuotaPlan(batched_lookup_units(cap)))
            ref = AccountRef(account)
            actual = 1
            try:
                if source == "liked_videos":
                    videos = await self.provider.list_liked_videos(ref, limit=cap)
                    rows = [
                        Observation(
                            v.published_at,
                            v.id,
                            v.channel_id,
                            v.category_id,
                            duration_seconds=v.duration_seconds,
                        )
                        for v in videos
                    ]
                elif source == "subscriptions":
                    subs = await self.provider.list_subscriptions(ref)
                    rows = [
                        Observation(s.subscription_created_at, channel_id=s.channel_id)
                        for s in subs
                    ]
                else:
                    items = await self.provider.list_playlist_items(ref, playlist)
                    rows = [
                        Observation(i.playlist_item_added_at, video_id=i.video_id) for i in items
                    ]
                actual = max(1, batched_lookup_units(min(cap, len(rows))))
            finally:
                reservation.commit(QuotaPlan(actual))
            limited = len(rows) > cap or (source == "liked_videos" and len(rows) == cap)
            coverage = Coverage(
                source=source,
                unit=LABELS[source][0],
                time_basis=LABELS[source][1],
                fetched_count=min(cap, len(rows)),
                reported_total=None,
                cap=cap,
                truncated=limited,
                truncation_reason="item cap reached" if limited else None,
                fetched_at=datetime.now(UTC),
                from_cache=False,
            )
            signals = LoadedSignals(items=rows[:cap], coverage=coverage)
            if not limited:
                with session_scope(self.engine) as session:
                    cache = CacheStore(ScopedSession(session, principal))
                    cache.purge_expired()
                    cache.put(
                        SIGNAL_KIND,
                        key,
                        signals.model_dump(mode="json"),
                        ttl=timedelta(hours=self.settings.account_cache_ttl_hours),
                    )
            signals._detail_reservation = detail_hold
            holds.pop_all()
            return {source: signals}
