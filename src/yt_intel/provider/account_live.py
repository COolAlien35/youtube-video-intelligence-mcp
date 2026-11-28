"""Policy-gated live YouTube Data API v3 account provider."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

from yt_intel.common.errors import AppError, ErrorCode
from yt_intel.provider.account import (
    Page,
    parse_liked_videos_response,
    parse_playlist_items_response,
    parse_playlists_response,
    parse_subscriptions_response,
)
from yt_intel.provider.error_mapping import map_api_error

if TYPE_CHECKING:
    import httpx

    from yt_intel.common.types import Principal
    from yt_intel.config.settings import Settings
    from yt_intel.provider.account_models import (
        LikedVideo,
        PlaylistItem,
        PlaylistSummary,
        Subscription,
    )

_YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"
_READONLY_SCOPE = "https://www.googleapis.com/auth/youtube.readonly"


class PolicyGateClosedError(AppError):
    """Raised when live account access is attempted while POL-04/POL-05 gates are closed."""

    def __init__(self, message: str = "Live account access is disabled by policy gates") -> None:
        super().__init__(ErrorCode.POLICY_GATE_CLOSED, message)


class AccessTokenProvider(Protocol):
    """Minimal token-source contract needed by LiveAccountProvider."""

    def access_token(self, principal: Principal, *, required_scopes: tuple[str, ...]) -> str:
        """Return an in-memory access token for *principal*."""
        ...


class LiveAccountProvider:
    """Live YouTube Data API v3 account adapter gated by POL-04, POL-05, and live flag."""

    def __init__(
        self,
        settings: Settings,
        token_source: AccessTokenProvider,
        *,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        if not (settings.pol_04_open and settings.pol_05_open and settings.live_youtube_enabled):
            raise PolicyGateClosedError(
                "Live YouTube account provider requires POL-04, POL-05, and live_youtube_enabled"
            )
        if http_client is None:
            import httpx as httpx_mod

            http_client = httpx_mod.AsyncClient(base_url=_YOUTUBE_API_BASE, timeout=15.0)
        self._client = http_client
        self._token_source = token_source

    async def _get_json(
        self,
        principal: Principal,
        path: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        token = self._token_source.access_token(principal, required_scopes=(_READONLY_SCOPE,))
        response = await self._client.get(
            path,
            params=params,
            headers={"Authorization": f"Bearer {token}"},
        )
        if response.status_code != 200:
            reason = "backendError"
            try:
                body = response.json()
                errors = body.get("error", {}).get("errors", [])
                if errors and isinstance(errors[0], dict):
                    reason = str(errors[0].get("reason", reason))
            except Exception:  # noqa: S110
                pass
            raise map_api_error(response.status_code, reason)
        payload = response.json()
        if not isinstance(payload, dict):
            raise AppError(ErrorCode.UPSTREAM_ERROR, "YouTube API returned non-object JSON")
        return payload

    async def list_liked_videos(
        self,
        principal: Principal,
        *,
        page_token: str | None = None,
        page_size: int = 50,
    ) -> Page[LikedVideo]:
        params: dict[str, Any] = {
            "part": "snippet,contentDetails",
            "myRating": "like",
            "maxResults": page_size,
        }
        if page_token is not None:
            params["pageToken"] = page_token
        raw = await self._get_json(principal, "/videos", params)
        return parse_liked_videos_response(raw)

    async def list_subscriptions(
        self,
        principal: Principal,
        *,
        page_token: str | None = None,
        page_size: int = 50,
    ) -> Page[Subscription]:
        params: dict[str, Any] = {
            "part": "snippet",
            "mine": "true",
            "maxResults": page_size,
        }
        if page_token is not None:
            params["pageToken"] = page_token
        raw = await self._get_json(principal, "/subscriptions", params)
        return parse_subscriptions_response(raw)

    async def list_playlists(
        self,
        principal: Principal,
        *,
        page_token: str | None = None,
        page_size: int = 50,
    ) -> Page[PlaylistSummary]:
        params: dict[str, Any] = {
            "part": "snippet,contentDetails",
            "mine": "true",
            "maxResults": page_size,
        }
        if page_token is not None:
            params["pageToken"] = page_token
        raw = await self._get_json(principal, "/playlists", params)
        return parse_playlists_response(raw)

    async def list_playlist_items(
        self,
        principal: Principal,
        playlist_id: str,
        *,
        page_token: str | None = None,
        page_size: int = 50,
    ) -> Page[PlaylistItem]:
        params: dict[str, Any] = {
            "part": "snippet",
            "playlistId": playlist_id,
            "maxResults": page_size,
        }
        if page_token is not None:
            params["pageToken"] = page_token
        raw = await self._get_json(principal, "/playlistItems", params)
        return parse_playlist_items_response(raw)
