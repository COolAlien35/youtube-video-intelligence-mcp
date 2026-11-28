# Release Notes — `v1.0.0-rc.1`

> **Important:** **Live YouTube access is disabled** (`YT_INTEL_LIVE_YOUTUBE_ENABLED=false`, `YT_INTEL_PLAYLIST_WRITES_ENABLED=false`) until written `POL-01`–`POL-08` determinations arrive. Promote to `v1.0.0` only after written clearance is recorded in [`docs/policy/gate_status.md`](docs/policy/gate_status.md).

## Features by Functional Requirement
- **FR-1 (`similar_videos`):** Canonical seed resolution (`seed.metadata` labelled untrusted) and bounded `POOL=50` video discovery (stacked on `p4-b-*`).
- **FR-2 (`similar_channels`):** Exact channel ID/handle parsing and bounded ranked channel discovery (stacked on `p4-d-*`).
- **FR-3 (`recommendations`):** Account-signal loader & cache foundation (`AccountSignalsLoader`); recommendation tool handler pending.
- **FR-4 (`engagement_analysis`):** Descriptive UTC-window metrics and duration bands over authorized account signals (stacked on `p5-d-*`).
- **FR-5 (`propose_playlist`, `confirm_execute_playlist`, `operation_status` & `video-to-playlist` skill):** `WriteProvider` protocol (`#89`), Phase 6 error & `sanitize_untrusted()` contracts, `Capability.PLAYLIST_WRITE` gating, packaged `SKILL.md`, structural validator, trace evaluation, and Demo F corpus/skeleton (`#95`–`#97`); executor/proposal services pending team merge.

## Security Posture, Retention & Privacy
- **Authentication & Isolation:** Supabase JWKS (`ES256`/`RS256`), strict Origin allow-list, HTTPS enforcement in `prod`, principal-scoped SQLite/WAL & cache, AES-256-GCM encrypted Google grants with refresh-token rotation.
- **Retention Windows (`DATA-22`–`26`):** `5` min (unexecuted proposals, approval handles, OAuth state), `24` h (terminal proposals & operations), `7` days (deletion & revocation backstop), `30` days (API cache ceiling from `fetched_at`).
- **External Content:** Disconnecting or deleting local data leaves playlists already created on YouTube in the user's YouTube account.

## Known Limitations & Quota Implications
- Shared daily caps: `2,000` common units (`50 + 50N` per playlist) and `20` `search.list` calls/day; account signal caps (`1,000` likes, `500` subscriptions, `200` playlists).
- Watch history is not available via YouTube Data API v3; metadata similarity does not assess factual quality.

## Gate Status & Verification Summary
- **Policy Gates:** All `POL-01`–`POL-08` gates are `closed` by default (see [`docs/policy/gate_status.md`](docs/policy/gate_status.md)).
- **Person D Checks:** `test_phase6_contracts.py` (26 passed), `test_validate_skill.py` (6 passed), `test_skill_traces.py` (11 passed), `test_gates.py` (6 passed), `test_demo_f_prompt_injection.py` (1 passed, 1 skipped awaiting A/B), `test_check_docs.py` (4 passed), `test_policy_status.py` (2 passed).
- **Team Gate Pending:** A's retention/recovery/Render runbook, B's security review & `v1.0.0-rc.1` tag, C's Demos A–G, ranking eval, coverage report & `--strict` RTM pass. See [`docs/release/evidence.md`](docs/release/evidence.md).
