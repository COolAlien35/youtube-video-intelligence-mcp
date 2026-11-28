# Project Query Log (`yt-intel-mcp`)

## Phase 6 & 7 Queries

### Q1: What gates and settings must be open before live playlist writes are allowed?
- **Answer:** `PolicyGates.playlist_write_allowed()` requires `YT_INTEL_PLAYLIST_WRITES_ENABLED=true` **and** valid open evidence for `POL-04`, `POL-05`, `POL-07`, and `POL-08`.
- **Sources:** [`src/yt_intel/policy/gates.py`](../../../src/yt_intel/policy/gates.py), [`docs/policy/write_gating.md`](../../../docs/policy/write_gating.md)

### Q2: How are untrusted video titles and descriptions prevented from triggering writes?
- **Answer:** Display text is sanitized via `sanitize_untrusted()`, `skills/video-to-playlist/SKILL.md` forbids treating metadata as instructions or calling `confirm_execute_playlist` without explicit user confirmation, and `ApprovalInvalidError` never echoes candidate handles.
- **Sources:** [`src/yt_intel/common/untrusted.py`](../../../src/yt_intel/common/untrusted.py), [`skills/video-to-playlist/SKILL.md`](../../../skills/video-to-playlist/SKILL.md), [`tests/e2e/test_demo_f_prompt_injection.py`](../../../tests/e2e/test_demo_f_prompt_injection.py)

### Q3: What happens to YouTube playlists after a user disconnects or deletes local data?
- **Answer:** Local tokens, proposals, operations, and caches are purged within the 7-day deletion deadline, while playlists already created on YouTube remain in the user's YouTube account.
- **Sources:** [`docs/privacy_policy.md`](../../../docs/privacy_policy.md), [`docs/data_deletion.md`](../../../docs/data_deletion.md)
