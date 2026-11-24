# Logical data model and retention

Draft implementation contracts for DATA-01–26, SEC-06–19, NFR-01–12 and POL-04/05. Column names below are proposed logical fields. The SRS defines behavior and lifetimes. Physical DDL and tooling require implementation review.

| Entity | Key and logical columns | Scope, retention and integrity |
|---|---|---|
| Principal | principal_key PK, issuer, subject | Unique verified issuer/subject pair; tenant root. Purge associated personal data on deletion. |
| Google grant | principal_key + account_ref, ciphertext, nonce, key_version, granted_scopes, status | Bind to principal and account. Key material lives outside SQLite. Stop using revoked grants immediately. |
| Daily quota | quota_day PK, common_used, common_reserved, search_calls_used, search_calls_reserved | Shared across all principals. Each field belongs to its own bucket; midnight Pacific selects a new day. Historical retention TBC. |
| Quota reservation | reservation_id PK, quota_day FK, principal_key, workflow_id, reserved costs, state | Reserve both buckets in one transaction or change neither. Settle/release against that reservation. Historical retention TBC. |
| Workflow limits | principal_key + workflow_id, started_at, active state | Per-principal active count and rolling one-minute start window. Two active and five starts/minute under ADR-09. |
| Cache entry | principal_key + category + canonical resource ID, account_ref when applicable, fetched_at, expires_at, payload | Tenant-scoped public metadata, private account signals and derived results must retain distinct classifications and source times. |
| Proposal | principal_key + proposal_id, account_ref, target_channel, title, description, visibility, constraints, digest, state, expires_at, single-use approval reference | Bind approval to the immutable snapshot. Enforce expiry on access even if cleanup has not run. |
| Proposal item | principal_key + proposal_id + position, canonical_video_id, runtime, language | Preserve approved order, reject duplicate IDs and enforce strict constraints on server. Same scope and lifetime as parent. |
| Operation | principal_key + operation_id, proposal_id, target_playlist_id if known, state, timestamps | Record external outcome separately from local approval. Record an uncertain response before reconciliation. |
| Operation item | principal_key + operation_id + position, video_id, external_item_id if known, outcome | Reconcile each item's status before safe continuation. Inherit parent retention. |
| Deletion request | principal_key + request_id, requested_at, deadline, progress, completed_at | Track purge across stores. Lifetime of a minimal post-purge receipt is TBC. |
| Policy compliance ledger | evidence_id, gate_id, scope, decision, evidence_ref, recorded_at, principal_key where consent-specific | Distinguish platform determinations from account consent. Missing or inapplicable evidence keeps the gate closed. Evidence retention is TBC. |

Tenant-owned tables require a non-null indexed principal_key. Include it in parent lookups and child relationships to prevent cross-principal joins. Private cache keys must distinguish linked accounts. The shared ledger aggregates reservations across all tenants. UTC instants retain separate video publication, subscription creation and playlist-item addition meanings. Unavailable liked-at times remain unknown.

## Retention matrix

| Deadline | Trigger and covered records | Enforcement |
|---|---|---|
| 5 minutes | Unexecuted proposal and single-use approval window | Reject stale or edited submissions; a fresh draft needs fresh confirmation. |
| Within 24 hours | Terminal proposals and completed/failed operations, including child items | Delete after termination. Reconciliation is an active state. |
| Within 7 calendar days | User deletion request or consent revocation | Purge associated data, including private cache and derived records. Explain that YouTube-hosted playlists/videos remain there. |
| At most 30 days | Stored YouTube API data, including public metadata | Refresh or delete by the ceiling. Earlier consent and deletion deadlines still apply. |

The SRS mentions 24h/30d caching in §6.1 but does not assign a precise TTL to every private signal or derived cache. TBC — confirm with team. Cleanup scheduling must meet the deadlines even after a restart.

## Proposal and operation transitions

| Current state | Permitted outcome | Precondition or effect |
|---|---|---|
| Draft / Proposed | Approved, Rejected, Superseded, Expired | Preview available, zero upstream writes. |
| Approved | Creating, Expired, Superseded | Consume approval once, for the same principal, account, channel and digest. |
| Creating | Completed, Partially Completed, Failed, Outcome Uncertain | Record each known outcome. A lost response does not prove failure. |
| Partially Completed / Outcome Uncertain | Reconciliation | Inspect the target playlist and local item records before retry. |
| Reconciliation | Creating, Completed, Partially Completed, Failed | Resume only writes established as safe. |
| Completed / Failed / Expired | New draft with a new identity | Original workflow is terminal. |

Rejected and Superseded appear as destinations in SRS §5.2. Their detailed cleanup classification is TBC — confirm with team.

## Open questions

Which migration tool and recovery procedure will A adopt? What is the maximum reconciliation lifetime? Which cache TTLs and evidence/receipt retention periods meet policy without retaining deleted personal data? What physical representation and constraints protect approval digests and prevent duplicate reservation settlement? Record agreed answers in the ADR/RTM change process.
