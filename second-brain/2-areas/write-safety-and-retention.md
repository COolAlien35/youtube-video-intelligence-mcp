# Write Safety & Retention (Refined)

Synthesized from [Phase 6 Skill & Write Safety](../3-resources/ingest/ingest_D_phase6_skill_and_write_safety.md), [Google Grants](../3-resources/ingest/ingest_B_google-grants.md), and [MCP Confirmation](../3-resources/ingest/ingest_B_mcp-confirmation.md).

## Dual-Lock Write Gating
- `Capability.PLAYLIST_WRITE` requires `POL-04`, `POL-05`, `POL-07`, and `POL-08` **plus** `YT_INTEL_PLAYLIST_WRITES_ENABLED=true` (`false` by default).
- Every write requires a 5-minute single-use approval handle bound to `(principal, google_sub, channel_id, snapshot_digest)`.

## Untrusted Metadata & Retention
- Video/playlist metadata is sanitized with `sanitize_untrusted()` (Unicode `NFC`, control/bidi-override stripping, length cap) and never interpreted as instructions.
- Retention windows: `5` min (unexecuted proposals/handles/OAuth state), `24` h (terminal proposals & operations), `7` days (deletion & revocation backstop), `30` days (API cache ceiling from `fetched_at`).
