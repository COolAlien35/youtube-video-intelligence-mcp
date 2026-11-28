# Ingest D · Phase 6 skill packaging, trace evaluation & write safety

- **Source:** Phase 6 Person D specification (`SK-01–05`, `FR-5`, `TQ-7`, Demo F) and repository implementation (`skills/video-to-playlist/`, `yt_intel.common.untrusted`, `yt_intel.policy.gates`).
- **Date:** 2026-11-28

## Key takeaways

1. **Untrusted metadata must be sanitized at the display boundary, not trusted for control flow:**
   `sanitize_untrusted(text, max_len=...)` normalizes to Unicode `NFC`, strips control characters (except `\n` and `\t`) and bidi-override characters (`U+202A–U+202E`, `U+2066–U+2069`), collapses excessive whitespace, and caps length with `…`. Error classes like `ApprovalInvalidError` must never echo user- or metadata-supplied handles.
2. **Skill governance is testable offline:**
   `scripts/validate_skill.py` enforces frontmatter, ordered 6-step workflow, stop-on-failure rules, and exact registry tool names (`similar_videos`, `propose_playlist`, `confirm_execute_playlist`, `operation_status`). `scripts/check_skill_traces.py` checks ordered tool calls, forbids writes before explicit confirmation, and verifies required report fields across 8 scenarios.
3. **Dual-lock write gating:**
   `Capability.PLAYLIST_WRITE` requires `POL-04`, `POL-05`, `POL-07`, and `POL-08` **plus** `settings.playlist_writes_enabled is True` (`PLAYLIST_WRITES_ENABLED=false` by default). Both must be open before `PolicyGates.playlist_write_allowed()` returns `True`.
