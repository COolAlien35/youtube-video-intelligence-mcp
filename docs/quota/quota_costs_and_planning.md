# Quota Costs and Planning — YouTube Data API v3

> **Source of truth:** `src/yt_intel/quota/costs.py` and `src/yt_intel/quota/preflight.py`.
> This document reflects the confirmed values in those files. Any discrepancy must be
> resolved by updating `costs.py` and posting a `type:change-request` issue.

---

## 1. Daily Quota Buckets

The YouTube Data API v3 exposes two independent daily quota buckets.
Both reset at **Pacific midnight** (UTC−8 / UTC−7 during daylight saving time).

| Bucket | Default daily cap | Governed by |
|---|---|---|
| **Common units** | 2 000 units | `QuotaService` common ledger |
| **Search calls** | 20 calls | `QuotaService` search ledger |

> **20 % per-workflow caps** (enforced by `QuotaPlanner.reserve()`):
> a single workflow may reserve at most 400 common units and 4 search calls.

---

## 2. Confirmed API Cost Table

Costs are verified against the
[official YouTube quota calculator](https://developers.google.com/youtube/v3/determine_your_quota_usage)
and the SRS §6.1 cost table.

### 2.1 Common-unit operations

| Operation | Units per call | Batch size | Notes |
|---|---|---|---|
| `videos.list` | 1 | 50 IDs/call | Use `batched_lookup_units(n, 50)` |
| `channels.list` | 1 | 50 IDs/call | Use `batched_lookup_units(n, 50)` |
| `captions.list` | 50 | — | Disabled in Phase 1–3 (feature-gated) |
| `captions.download` | 200 | — | Disabled in Phase 1–3 (feature-gated) |
| `playlists.insert` | 50 | — | Per playlist created |
| `playlistItems.insert` | 50 | — | **Per item** — multiply by item count |

### 2.2 Search operations

| Operation | Common units | Search calls | Notes |
|---|---|---|---|
| `search.list` | 100 | 1 | Burns **both** buckets simultaneously |

One `search.list` page returns up to 50 candidate videos
(the system default). Each additional page costs another 100 common units
and 1 search call.

### 2.3 TBC operations

The following costs appear in `costs.py` as **TBC** and must be verified before
any code path invokes them in production:

| Operation | TBC value | Action required |
|---|---|---|
| `videos.list` (`myRating=like`) | 1 unit / page-50 | Account liked videos; verify at the [quota calculator](https://developers.google.com/youtube/v3/determine_your_quota_usage); open `type:change-request` if different |
| `playlists.list` (`mine=true`) | 1 unit / page-50 | Account playlists; verify at the [quota calculator](https://developers.google.com/youtube/v3/determine_your_quota_usage); open `type:change-request` if different |
| `playlistItems.list` | 1 unit / page-50 | Account playlist items; same as above |
| `subscriptions.list` (`mine=true`) | 1 unit / page-50 | Account subscriptions; same as above |

---

## 3. Planning Flow

Every workflow that touches the YouTube provider must follow this sequence:

```
PrincipalLimiter.acquire_workflow(principal)   # concurrency + rate-limit gate
    │
    ├─ CacheStore.get_many(kind, keys)          # read cache; skip provider calls for hits
    │
    ├─ QuotaPlanner.reserve(principal, plan)    # atomic two-bucket preflight
    │       ├─ success → Reservation handle
    │       └─ QUOTA_EXCEEDED → AppError raised; Reservation never issued
    │
    ├─ <provider calls>                         # e.g. videos.list, search.list
    │
    ├─ CacheStore.put(kind, key, value)         # populate cache with fresh data
    │
    ├─ Reservation.commit(actual)               # settle actual usage, return surplus
    │       or
    └─ Reservation.release()                    # on failure — return all reserved units
```

### 3.1 Concurrency and start-rate limits (`PrincipalLimiter`)

`PrincipalLimiter.acquire_workflow(principal)` is a context manager that:

1. Acquires a row lock on `workflow_limits` for the principal (SQLite `BEGIN IMMEDIATE`).
2. Rejects if **active concurrent workflows ≥ 2** →
   `AppError(ErrorCode.RATE_LIMITED, retryable=True)`.
3. Rejects if **starts in the last 60 s ≥ 5** →
   `AppError(ErrorCode.RATE_LIMITED, retryable=True, retry_after=N)`.
4. Marks the slot active on enter; clears it in `finally`.

### 3.2 Cache lookup (`CacheStore`)

`CacheStore` wraps the `cache_entries` table with principal-scoped isolation
(via `ScopedSession`). Read behaviour:

- `get(kind, key)` / `get_many(kind, keys)` return `CachedValue | None`.
- A hit is valid only if `now < min(expires_at, fetched_at + 30 days)`.
  The 30-day hard ceiling is re-checked on every read regardless of the stored
  `expires_at`, preventing stale cache entries from living indefinitely.
- Default TTL on write: **24 hours** (clamped to `min(ttl, 30 days)`).
- Maximum payload: **256 KiB** per entry.
  Larger payloads raise `AppError(ErrorCode.INVALID_INPUT)`.

### 3.3 Preflight reservation (`QuotaPlanner`)

`QuotaPlanner.reserve(principal, plan)` calls `QuotaService.reserve()` atomically:

- Checks both buckets simultaneously (no TOCTOU window).
- On success returns a `Reservation` handle with `.commit(actual)` / `.release()`.
- On failure logs `quota_preflight_rejected` with a hashed principal key
  (first 16 hex chars of SHA-256) and the current `request_id` — never the
  raw principal key or any credential.

### 3.4 Batched lookup helper

```python
from yt_intel.quota.preflight import batched_lookup_units

units = batched_lookup_units(n_ids=120, batch=50)
# → 3  (ceil(120 / 50) = 3 videos.list or channels.list calls)
```

---

## 4. Cache Scope Decision

Cache rows are **principal-scoped** (tenant-isolated via `ScopedSession`).

**Rationale:** consistent with the Demo G security review (ADR register, §cache-scope).
A cross-principal shared cache would require deduplication logic, increase blast radius
on a cache-poisoning attack, and complicate the per-principal audit trail.
The quota savings from sharing are modest relative to the risk.

---

## 5. Search Candidate Pool

One `search.list` call returns **up to 50 candidates** (one page).
Fetching additional pages is not performed by default because each additional page
costs another 100 common units + 1 search call — the same price as the first page.

If the pool must grow beyond 50, the caller must explicitly plan the multi-page
cost with `cost_of("search.list", count=N)` before reserving.

---

## 6. References

| Resource | Location |
|---|---|
| Cost table (source of truth) | [`src/yt_intel/quota/costs.py`](../../src/yt_intel/quota/costs.py) |
| Preflight facade | [`src/yt_intel/quota/preflight.py`](../../src/yt_intel/quota/preflight.py) |
| Quota service ledger | [`src/yt_intel/quota/service.py`](../../src/yt_intel/quota/service.py) |
| Principal limiter | [`src/yt_intel/quota/limits.py`](../../src/yt_intel/quota/limits.py) |
| Cache store | [`src/yt_intel/cache/store.py`](../../src/yt_intel/cache/store.py) |
| SRS §6.1 | `docs/SRS_v1.0.docx` |
| ADR register | [`docs/Architecture_Decision_Records_v1.0.md`](../Architecture_Decision_Records_v1.0.md) |
| Official quota calculator | <https://developers.google.com/youtube/v3/determine_your_quota_usage> |
