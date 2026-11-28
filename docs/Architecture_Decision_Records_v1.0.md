# Architecture decision register v1.0

Source: YouTube Video Intelligence MCP Server SRS v1.0, 9 November 2026, Appendix B and §§2–10. Appendix B closes the design decisions in groups. The record numbers below follow the supplied Person B brief’s proposed ordering. Team confirmation of individual mappings is pending. Closed design status does not establish implementation, team sign-off or platform clearance.

## DEC-01–22 crosswalk

The left column preserves the source’s group boundaries. ADR associations are proposed trace links. The SRS does not publish a separate one-line entry for every DEC.

| Decision IDs | Source summary in order | Related ADRs or direct requirement |
|---|---|---|
| DEC-01–06 | Remote Streamable HTTP; purpose-specific tools; TF-IDF/cosine; descriptive UTC analytics; strict playlist caps/private default; metadata synopsis. | 01 (transport/tools), 08 (ranking), 11 (analytics). Playlist and synopsis behavior also trace to FR-5 and NFR-25–32. |
| DEC-07–12 | 20% quota caps; CSV RTM; 24h/5m lifecycle; separate MCP and Google OAuth; offline ranking evaluation; P95 ranking target. | 09 (caps), 10 (lifecycle), 03/05 (identity), 08 (evaluation/performance). Trace the CSV directly to §9. |
| DEC-13–16 | GitHub/Obsidian workflow; own-channel check; MRTR confirmation; portable video-to-playlist skill. | 05 (channel eligibility), 01/07 (confirmation). Governance and skill packaging trace directly to §8. |
| DEC-17–22 | Fail-closed policy gates; canonical URL/handle resolution; bounded search; single-instance WAL ledger. | 01/05 (exposure and access), 08 (canonical inputs), 09 (search budget), 04/07 (ledger). Appendix B gives four summaries for six IDs. Individual assignments: TBC — confirm with team. |

### Individual lookup for DEC-01–16

Proposed by order within each source row. TBC — confirm with team. For DEC-17–22 use the grouped entry above until the individual definitions are supplied.

| ID | Summary | Related ADR number or SRS reference |
|---|---|---|
| DEC-01 | Remote Streamable HTTP | 01 |
| DEC-02 | Purpose-specific tools | 01, IF-07–11 |
| DEC-03 | TF-IDF and cosine similarity | 08 |
| DEC-04 | Descriptive UTC analytics | 11 |
| DEC-05 | Strict playlist caps and private default | FR-5 |
| DEC-06 | Metadata-based synopsis | NFR-25–32 |
| DEC-07 | 20% quota caps | 09 |
| DEC-08 | CSV traceability matrix | SRS §9 |
| DEC-09 | 24-hour cleanup and five-minute expiry | 10 |
| DEC-10 | Separate MCP and Google authorization | 03, 05 |
| DEC-11 | Offline Precision@K and NDCG@K | 08 |
| DEC-12 | Ranking P95 target for 100 items | 08, NFR-07c–07e |
| DEC-13 | GitHub and Obsidian workflow | SRS §8 |
| DEC-14 | Check the account’s own channel | 05 |
| DEC-15 | MRTR confirmation | 01, 07 |
| DEC-16 | Portable video-to-playlist skill | SRS §8 |

## ADR-01 — MCP transport and target client

- Status: Closed (design decision recorded 9 Nov 2026)
- Owner / Reviewer: S. Banerjee / H. Kumar, P. Pandey
- Related: DEC group(s) 01–06, 13–16; IF-01–11, SEC-20
- Distilled project evidence: [release-evidence](https://github.com/COolAlien35/youtube-video-intelligence-mcp/blob/0339721/brain/areas/release-evidence.md)

### Context

The client must show a typed preview and return confirmation across requests.

### Decision

Target Claude Desktop using MCP 2026-07-28 Streamable HTTP and the official Python SDK v2. Return input_required when confirmation is needed. Validate the caller, approved snapshot and single-use handle before execution.

### Alternatives considered

Appendix B records the selected design only. TBC — confirm with team whether alternatives were evaluated.

### Consequences

A compatible client can complete the preview flow. Loss of client support or an edited proposal must leave the operation unwritten.

### Verification

TQ-9–13, TQ-28–34: exercise confirmation, edits and Origin rejection.

## ADR-02 — Application stack

- Status: Closed (design decision recorded 9 Nov 2026)
- Owner / Reviewer: S. Banerjee / H. Kumar, P. Pandey
- Related: DEC group(s) 01–06; NFR-13–24
- Distilled project evidence: [release-evidence](https://github.com/COolAlien35/youtube-video-intelligence-mcp/blob/0339721/brain/areas/release-evidence.md)

### Context

The server needs repeatable installs, HTTP handling and persistent transactions.

### Decision

Use Python 3.12 with uv, FastAPI and SQLAlchemy. Keep the provider interface replaceable in tests.

### Alternatives considered

Appendix B records the selected design only. TBC — confirm with team whether alternatives were evaluated.

### Consequences

A locked build and typed interfaces support reproducible tests. Dependency and schema changes require coordinated review.

### Verification

TQ-5–8, TQ-14–18: reproduce the locked build and exercise storage against fixtures.

## ADR-03 — Service identity

- Status: Closed (design decision recorded 9 Nov 2026)
- Owner / Reviewer: S. Banerjee / H. Kumar, P. Pandey
- Related: DEC group(s) 07–12; IF-17–23, SEC-01–05
- Distilled project evidence: [release-evidence](https://github.com/COolAlien35/youtube-video-intelligence-mcp/blob/0339721/brain/areas/release-evidence.md)

### Context

Several users share one MCP service and may connect different Google accounts.

### Decision

Use Supabase Auth as OAuth 2.1/OIDC provider. Derive each principal from a validated issuer and subject. Bind the Google grant to that principal.

### Alternatives considered

Appendix B records the selected design only. TBC — confirm with team whether alternatives were evaluated.

### Consequences

A subject can be scoped to its issuing authority. Cross-tenant lookups must be tested, including cache hits and operation status.

### Verification

TQ-28–34: use two principals and verify isolation and authenticated transport.

## ADR-04 — Deployment and persistent disk

- Status: Closed (design decision recorded 9 Nov 2026)
- Owner / Reviewer: S. Banerjee / H. Kumar, P. Pandey
- Related: DEC group(s) 17–22; OPS-01–12
- Distilled project evidence: [persistent-state](https://github.com/COolAlien35/youtube-video-intelligence-mcp/blob/0339721/brain/areas/persistent-state.md)

### Context

Quota reservations and operation progress must survive a service restart.

### Decision

Deploy one Render Web Service in Singapore with SQLite on the persistent disk at /var/data. Use Supabase Auth in ap-southeast-1.

### Alternatives considered

Appendix B records the selected design only. TBC — confirm with team whether alternatives were evaluated.

### Consequences

A restart can reuse durable state. The initial service has no uptime, RTO or RPO commitment.

### Verification

SRS §10 and Appendix B: inspect the deployment and verify restart persistence and health.

## ADR-05 — Google project and delegated scopes

- Status: Closed (design decision recorded 9 Nov 2026)
- Owner / Reviewer: P. Pandey, S. Banerjee / H. Kumar
- Related: DEC group(s) 07–12, 13–16; IF-12–23, POL-04/05
- Distilled project evidence: [live-access-decisions](https://github.com/COolAlien35/youtube-video-intelligence-mcp/blob/0339721/brain/areas/live-access-decisions.md)

### Context

Read-only research and playlist writes require different user permissions.

### Decision

Use one GCP project. Request read access by default and incrementally obtain write scopes for playlist creation. Check the authorized account has a channel before writing.

### Alternatives considered

Appendix B records the selected design only. TBC — confirm with team whether alternatives were evaluated.

### Consequences

A read-only user need not grant write access. Expired or revoked grants require reauthorization; a missing channel stops the write.

### Verification

TQ-9–13, TQ-19–27: verify scope escalation, expired grants and channel-required handling.

## ADR-06 — Refresh-token storage

- Status: Closed (design decision recorded 9 Nov 2026)
- Owner / Reviewer: P. Pandey, S. Banerjee / H. Kumar
- Related: DEC group(s) 07–12; SEC-06–09
- Distilled project evidence: [release-evidence](https://github.com/COolAlien35/youtube-video-intelligence-mcp/blob/0339721/brain/areas/release-evidence.md)

### Context

A persisted Google refresh token can authorize future account access.

### Decision

Encrypt persisted refresh tokens using AES-256-GCM through Python cryptography. Supply a 32-byte hosting secret and record the key version.

### Alternatives considered

Appendix B records the selected design only. TBC — confirm with team whether alternatives were evaluated.

### Consequences

Storage contains ciphertext. Recovery and rotation depend on access to the matching key version; keep keys out of repositories and diagnostics.

### Verification

TQ-9–13: round-trip synthetic tokens and reject altered ciphertext.

## ADR-07 — SQLite WAL and atomic reservations

- Status: Closed (design decision recorded 9 Nov 2026)
- Owner / Reviewer: P. Pandey, S. Banerjee / H. Kumar
- Related: DEC group(s) 13–16, 17–22; NFR-01–12, DATA-07–15
- Distilled project evidence: [persistent-state](https://github.com/COolAlien35/youtube-video-intelligence-mcp/blob/0339721/brain/areas/persistent-state.md)

### Context

Concurrent requests share a quota ceiling and may contend for the same approval.

### Decision

Use SQLite WAL with atomic quota and approval transactions. Preflight the whole workflow and consume the immutable approval once.

### Alternatives considered

Appendix B records the selected design only. TBC — confirm with team whether alternatives were evaluated.

### Consequences

Transactions prevent double reservation and approval reuse. An external write can still succeed when its response is lost, requiring reconciliation.

### Verification

TQ-5–8, TQ-9–13: race reservations and approvals; reconcile interrupted writes.

## ADR-08 — Deterministic similarity

- Status: Closed (design decision recorded 9 Nov 2026)
- Owner / Reviewer: A. Singh, S. Banerjee / P. Pandey, H. Kumar
- Related: DEC group(s) 01–06, 07–12; FR-1, FR-2, NFR-07c–07e
- Distilled project evidence: [live-access-decisions](https://github.com/COolAlien35/youtube-video-intelligence-mcp/blob/0339721/brain/areas/live-access-decisions.md)

### Context

Input sources expose metadata rather than a related-videos endpoint.

### Decision

Apply TF-IDF and cosine similarity. For the documented video baseline, weight title 0.50, description 0.30, tags 0.15 and category 0.05. Break score ties by canonical ID.

### Alternatives considered

Appendix B records the selected design only. TBC — confirm with team whether alternatives were evaluated.

### Consequences

Results can be reproduced and explained. Missing fields and policy limits constrain which comparisons are possible.

### Verification

TQ-1–4, TQ-28–34: test deduplication, ties, missing tags and offline Precision@K/NDCG@K.

## ADR-09 — Quota and per-principal fairness

- Status: Closed (design decision recorded 9 Nov 2026)
- Owner / Reviewer: A. Singh, S. Banerjee / P. Pandey, H. Kumar
- Related: DEC group(s) 07–12, 17–22; NFR-01–07e
- Distilled project evidence: [release-evidence](https://github.com/COolAlien35/youtube-video-intelligence-mcp/blob/0339721/brain/areas/release-evidence.md)

### Context

One noisy principal can exhaust the shared project allowance.

### Decision

Cap baseline daily use at 20 search.list calls and 2,000 common units, each within 20% of its approved allowance. Reset at Pacific midnight. Allow two concurrent workflows and five starts/minute per principal.

### Alternatives considered

Appendix B records the selected design only. TBC — confirm with team whether alternatives were evaluated.

### Consequences

A request may be denied while other users still work. Keep the search-call counter distinct from common units and reject over-budget work before provider access.

### Verification

TQ-5–8, TQ-19–27, TQ-28–34: test concurrent preflight, cap exhaustion and the Pacific day boundary.

## ADR-10 — Cleanup and lifecycle

- Status: Closed (design decision recorded 9 Nov 2026)
- Owner / Reviewer: A. Singh, S. Banerjee / P. Pandey, H. Kumar
- Related: DEC group(s) 07–12; DATA-07–15, DATA-22–26
- Distilled project evidence: [release-evidence](https://github.com/COolAlien35/youtube-video-intelligence-mcp/blob/0339721/brain/areas/release-evidence.md)

### Context

Immutable proposals, completed work and external API data have different lifetimes.

### Decision

Expire unexecuted proposals after five minutes. Purge terminal proposals and completed/failed operations within 24 hours. Apply deletion/revocation and API-data ceilings separately.

### Alternatives considered

Appendix B records the selected design only. TBC — confirm with team whether alternatives were evaluated.

### Consequences

Storage cleanup limits exposure. Reconciliation needs live operation state until the outcome is known; its maximum age needs team confirmation.

### Verification

TQ-19–27: advance an injected clock across expiry, cleanup and deletion deadlines.

## ADR-11 — Descriptive engagement metrics

- Status: Closed (design decision recorded 9 Nov 2026)
- Owner / Reviewer: A. Singh, S. Banerjee / P. Pandey, H. Kumar
- Related: DEC group(s) 01–06; FR-4, NFR-25–32, POL-01–08
- Distilled project evidence: [live-access-decisions](https://github.com/COolAlien35/youtube-video-intelligence-mcp/blob/0339721/brain/areas/live-access-decisions.md)

### Context

The API supplies likes, subscriptions and playlists, with incomplete timestamp coverage.

### Decision

Report supported channel/category counts, trends, duration preferences and period comparisons. Label source, unit, coverage and time basis. Never derive a liked-at timestamp or claim watch history.

### Alternatives considered

Appendix B records the selected design only. TBC — confirm with team whether alternatives were evaluated.

### Consequences

Users can interpret the evidence behind each comparison. Sparse or truncated samples must produce qualified results; policy gates still apply.

### Verification

TQ-1–4, TQ-19–27: inspect labels, insufficient samples and closed-gate behavior.
