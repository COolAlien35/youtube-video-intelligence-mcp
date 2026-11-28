# Account Signals & Caching Architecture (Phase 5)

> **Scope:** Principal-scoped account signals (`LIKED_VIDEOS`, `SUBSCRIPTIONS`, `PLAYLISTS`,
> `PLAYLIST_ITEMS`) loaded by `AccountSignalsLoader` (`src/yt_intel/account/loader.py`).

---

## 1. Signal Models & Timestamp Semantics

All account data models live in `src/yt_intel/provider/account_models.py` as frozen dataclasses.
Provider metadata is treated as untrusted: invalid fields are recorded in `invalid_fields` and
coerced to `None` rather than crashing pagination.

| SignalKind | Model | Time Basis (`Coverage.time_basis`) | Notes |
|---|---|---|---|
| `LIKED_VIDEOS` | `LikedVideo` | `video_published_at` | **No `liked_at` field** — the YouTube Data API v3 `videos.list?myRating=like` endpoint does not expose when a video was liked. |
| `SUBSCRIPTIONS` | `Subscription` | `subscription_created_at` | `snippet.publishedAt` from `subscriptions.list?mine=true`. |
| `PLAYLISTS` | `PlaylistSummary` | `None` | Owned playlists from `playlists.list?mine=true`; carries no time basis. |
| `PLAYLIST_ITEMS` | `PlaylistItem` | `playlist_item_added_at` | `snippet.publishedAt` from `playlistItems.list`. |

> **Watch history:** The server never claims watch-history access (`N/A` in YouTube Data API v3).

---

## 2. Coverage Labels (`Coverage`)

Every `SignalSet[T]` carries a `Coverage` dataclass describing data provenance and completeness:

- `source`: `"provider"`, `"partial_provider"` (interrupted after ≥1 page), `"cache"`, or `"fixture"`
- `unit`: `"liked_videos"`, `"subscriptions"`, `"playlists"`, or `"playlist_items"`
- `time_basis`: `"video_published_at"`, `"subscription_created_at"`, `"playlist_item_added_at"`, or `None`
- `fetched_count`: number of items returned
- `reported_total`: `pageInfo.totalResults` reported by the provider (if present)
- `cap`: configured cap applied during fetch (`account_like_cap`, `account_subscription_cap`, `account_playlist_cap`, `account_playlist_items_cap`)
- `truncated` / `truncation_reason`: `True` when a cap is reached or pagination is interrupted
- `fetched_at`: UTC timestamp when data was fetched
- `from_cache`: `True` when served from `CacheStore`

---

## 3. Principal-Scoped Caching & Purge Hooks

- **Isolation:** Every cache entry is stored via `CacheStore` backed by `ScopedSession(session, principal)`. Cache keys for account signals are SHA-256 digests of `(kind, principal_key, params)` under dedicated categories (`account_liked`, `account_subscriptions`, `account_playlists`, `account_playlist_items`).
- **TTL & Ceiling:** Default TTL is `account_cache_ttl_hours = 24` hours, clamped on write and re-checked on read against the hard 30-day policy ceiling (`MAX_CACHE_TTL`).
- **Refresh:** Passing `refresh=True` bypasses the cache read and re-fetches from the provider.
- **Purge Hooks (`CacheStore`):**
  - `CacheStore.purge_principal()` deletes all cache entries belonging to the scoped principal (used by `disconnect_google` and Phase 7 data-deletion flows).
  - `CacheStore.purge_kind(kind)` deletes all cache entries of a single category for the scoped principal.

---

## 4. Policy Gates, Token Source & Logging

- **Policy Gates:** `LiveAccountProvider` (`src/yt_intel/provider/account_live.py`) requires `pol_04_open`, `pol_05_open`, and `live_youtube_enabled` to all be `True` before constructing an `httpx.AsyncClient` or issuing any network call. Closed gates raise `PolicyGateClosedError` (`ErrorCode.FORBIDDEN`).
- **Token Handling:** `TokenSource` (`src/yt_intel/security/token_source.py`) decrypts persisted refresh tokens on demand via `GrantRepo`, refreshes short-lived access tokens without caching or logging them, and re-encrypts rotated refresh tokens.
- **Logging:** Account signal logs record only `request_id`, `count`, `pages`, and `kind` — never video titles, channel titles, playlist titles, video/channel IDs, or OAuth tokens.
