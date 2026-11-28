# Playlist write policy gating

Playlist creation (`FR-5`) is the highest-risk capability in YouTube Video Intelligence MCP because it mutates a user's YouTube account. Live playlist writes are **fail-closed** by default and require both policy gate clearance and explicit runtime configuration.

## Gate mapping (`Capability.PLAYLIST_WRITE`)

In `yt_intel.policy.gates`, `Capability.PLAYLIST_WRITE` maps to:

| Gate | Requirement | Purpose |
|---|---|---|
| `POL-04` | Consented account data use | Verifies delegated Google OAuth consent and incremental write scope (`WriteScopeRequiredError` when absent) |
| `POL-05` | Compliance ledger & account scope | Audits write-gate checks, proposal approvals, and write attempts per principal |
| `POL-07` | Presentation & attribution | Ensures canonical YouTube links, derived labels, and required disclosures accompany created playlists |
| `POL-08` | Remote MCP service clearance | Blocks live YouTube API write access until written service guidance is recorded |

`PolicyGates.playlist_write_allowed(principal=...)` enforces **both**:
1. `settings.playlist_writes_enabled is True` (`PLAYLIST_WRITES_ENABLED`, default `false`).
2. `PolicyGates.live_youtube_allowed(Capability.PLAYLIST_WRITE, principal=principal)` (all four gates `POL-04`, `POL-05`, `POL-07`, `POL-08` open with valid evidence references).

## Per-proposal authorization & safety invariants

Even when fixture or gated write execution is enabled:
- **Zero writes before approval:** `propose_playlist` produces an immutable preview only.
- **Single-use MRTR approval:** `confirm_execute_playlist` requires a 5-minute single-use approval handle bound to the verified MCP `Principal`, Google account (`google_sub`), eligible YouTube `channel_id`, and SHA-256 snapshot digest.
- **Edit invalidation:** Any change to title, description, privacy/visibility, channel, or video order supersedes the proposal and invalidates prior approvals.
- **Write-before-call journaling:** Each `playlists.insert` and `playlistItems.insert` is journaled (`INSERTING`) before the upstream call and reconciled before any resume; writes are never blindly retried.
