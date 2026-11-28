# MCP server module contracts

Design draft against SRS §§2–7. The nine purposes are baselined by IF-07–11. The snake_case wire names and field groupings below are proposed for implementation review.

## Layers and ownership

```mermaid
flowchart LR
  transport[server / transport] --> tools[thin tool handlers] --> features[feature services]
  features --> provider[provider interface]
  features --> ranking
  features --> quota
  features --> proposals
  features --> policy
  features --> auth
  features --> storage
  quota --> storage
  proposals --> storage
  provider --> fixtures[synthetic adapter]
  provider --> live[policy-gated official adapter]
```

At ingress validate Origin and, in authenticated phases, the MCP access token. Bind the verified principal and diagnostic request ID to the call. Tool handlers validate schemas and route requests. Feature services coordinate policy, authorization, preflight and domain behavior. Only the provider interface reaches YouTube. Each tenant-owned storage access requires a principal predicate, including updates and deletes. Project-wide quota totals are explicitly shared. Enforce policy gates inside the server before protected computation or provider calls. IF-09a prohibits generic forwarding and bulk export.

## Proposed package tree and phase allocation

All paths below are children of src/yt_intel/. They describe intended ownership and boundaries.

| Package | Responsibility | First phase supported by available briefs |
|---|---|---|
| config/ | Validated settings and fail-closed live flag | 2, A |
| server/ | Streamable HTTP, Origin, context, health and auth integration point | 2, B |
| tools/ | Nine tool schemas and dispatch | 2, B, initially stubs |
| common/ | AppError, principal, UTC clock, request IDs, durations, canonical IDs and logging | 2, D |
| provider/ | Normalization, provider protocol, synthetic fixture implementation | 2, C |
| storage/ | Persistence, principal filters, WAL and transactions | 2, A |
| quota/ | Reservation, settlement, release, limits and Pacific-day accounting | 2, A |
| auth/ | Service identity, grant binding and Google authorization | 3, per Phase 2 auth handoff |
| ranking/ | Deterministic similarity and evidence for ranking | TBC — confirm with team |
| features/ | Search, recommendations and engagement orchestration | TBC — confirm with team |
| proposals/ | Immutable previews, approval, execution and reconciliation | TBC — confirm with team |
| policy/ | Capability-specific evidence and enforcement | TBC — confirm with team |

Phase 1 supplies documentation. Phase 2 supplies local foundations. Phase 3 introduces auth. Allocation across phases 4, 5, 6 and 7 is TBC — confirm with team; the seven-phase allocation table was absent from the reviewed materials.

## MCP tool catalogue

Return schema-defined JSON with diagnostic request ID. Include YouTube attribution and canonical links wherever a resource is displayed. Attach provenance to derived outputs. Each tool requires the authenticated MCP principal in the target service. Google authorization below refers to the separate delegated account grant.

| Proposed tool | Input and purpose | Structured result | Google authorization | Writes |
|---|---|---|---|---|
| similar_videos | Seed video URL or ID, bounded discovery | Ranked canonical videos, scores, factor explanations and coverage | Public reads only | None |
| similar_channels | Exact channel ID, handle or supported URL | Ranked channels, reasons or explained empty result | Public reads only | None |
| recommendations | Use linked account signals and bounded candidate set | Ranked videos, contributing signal sources and truncation | Read | None |
| engagement_analysis | Supported metric and period over account signals | Counts, units, coverage, time basis and comparisons | Read | None |
| propose_playlist | Topic, duration caps, language and visibility | Preview, ordered items, runtimes, channel, warnings, immutable reference | Read for account-bound preview | Local proposal only |
| confirm_execute_playlist | MRTR answer plus proposal-bound state | Outcome, operation reference, playlist link if known, per-item results | Write scope plus eligible channel | Approved playlist and item writes |
| operation_status | Principal-scoped operation reference | Status, reconciliation progress and per-item outcomes | No fresh grant for local status | None |
| disconnect | Connected account reference | Disconnect outcome and purge information | Existing grant if available for revocation | Revoke/unlink grant; no playlist change |
| delete_data | Principal-scoped deletion request | Receipt, purge deadline and external-content disclosure | No fresh grant for local deletion | Delete local account data |

Principal-scoped MCP resources are read-only. A confirmed playlist write requires both remote policy clearance and fresh authorization for the exact proposal.

## Provider boundary

The asynchronous contract batches video IDs, fetches channels, resolves exact channel references, runs bounded video search, lists liked videos, subscriptions, playlists and their items, and checks the caller’s own channel. Write methods create a playlist and insert an individual item. Reserve quota before access. Preserve page limits and unavailable IDs. Normalize durations to integer seconds or unknown; keep missing tags distinct from empty tags. Normalize timestamps to aware UTC while retaining their meaning. Map upstream errors once at this boundary using the [error model](error_model.md). Supply synthetic responses and deterministic faults through the fixture adapter. Never select the live adapter merely because credentials exist.

## Cross-cutting behavior

Validate non-secret configuration at startup. Keep raw credentials, user payloads and exception chains out of diagnostics. Correlate public errors and logs using the request ID. Use one canonical reference per entity for deduplication. Use UTC for stored instants and reporting; compute the quota-day label at midnight in America/Los_Angeles, including daylight-saving changes. See the [data model](data_model.md).

## Phase 2 changes · 25 November 2026

The [server skeleton](https://github.com/COolAlien35/youtube-video-intelligence-mcp/pull/14) mounts /mcp and exposes /health. Its outer request-ID middleware wraps Origin rejection, tool dispatch and HTTP errors. The factory refuses production startup before auth exists. Phase 3 replaces server.guards.get_principal; the SDK injects the principal without adding it to tool input schemas.

The [tool registry](https://github.com/COolAlien35/youtube-video-intelligence-mcp/pull/15) preserves all nine catalogue names. Each stub returns the same typed envelope with NOT_IMPLEMENTED. The SDK smoke tests exercise July discovery and legacy initialize separately. Neither flow invokes the provider. The frozen package dependency and real config integration await A. [SDK verification](https://github.com/COolAlien35/youtube-video-intelligence-mcp/pull/13)

## Phase 4 channel discovery

The registered MCP tool passes the verified principal and channel reference to SimilarChannelsService. The service parses locally, acquires a per-principal workflow slot and checks the principal's cached result. On a miss it reserves the maximum cost before the exact seed lookup. The cost table charges one common unit for the seed, 100 common units and one search call for the bounded page, and one common unit for up to 50 detail lookups in a single batch. Failed or empty workflows settle the calls they attempted. An over-budget reservation prevents all provider access.

A deterministic query combines the seed title and available keywords. The workflow drops the seed, repeated IDs and unavailable records. The proposed channel weights are 40% title, 40% description and 20% keywords, with no category contribution because category is absent from the channel model. TF-IDF cosine scores are computed per field across the seed and surviving pool. Ties use ascending channel ID. Search results are bounded and do not represent the full YouTube catalogue.

The fixture implementation uses the existing gated provider factory. Canonical result rows in SQLite carry a principal key, a handle lookup value and a 24-hour expiry. The cache reader checks both original fetch time and expiry. The current channel-specific cache and ranking adapters keep FR-2 runnable while A and C deliver their shared implementations. Maintainers should run the isolation, quota, ordering and MCP schema tests again after substituting those dependencies. Pool size and weights await team agreement. [Interface decision](https://github.com/COolAlien35/youtube-video-intelligence-mcp/issues/61) · [Tool contract](../tools/similar_channels.md)
