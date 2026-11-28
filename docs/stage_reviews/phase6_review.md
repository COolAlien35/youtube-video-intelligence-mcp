# Phase 6 stage review · Playlist creation & skill (Person D snapshot)

**Gate decision: hold.** This snapshot records Person D's completed deliverables on top of `main` (`c874300`, `#89` write provider protocol & operation types). Team integration and Demos A–E remain pending.

| Owner | Evidence | Status |
|---|---|---|
| A | [Write provider protocol, operation types, and settings (#89)](https://github.com/COolAlien35/youtube-video-intelligence-mcp/pull/89) | Merged on `main`. `FixtureWritePlaylistProvider`, `OperationRepo`, `PlaylistExecutor`, and `Reconciler` pending. |
| B | Proposal state machine, MRTR approval, `propose_playlist`, `confirm_execute_playlist`, `operation_status` | Pending (`tools/` currently stubs on `main`). |
| C | Constraint filtering (`yt_intel/playlists/constraints.py`) and Demos A, B, C, E | Pending. |
| D | Errors & `sanitize_untrusted`, `skills/video-to-playlist/SKILL.md`, `validate_skill.py`, `check_skill_traces.py`, `Capability.PLAYLIST_WRITE`, `docs/policy/write_gating.md`, privacy/deletion updates, `README.md` & tool docs, Demo F skeleton | Drafted & unit-tested offline; Demo F e2e execution awaits A + B. |

## Verification (Person D deliverables)

- **Contracts & untrusted sanitization:** `tests/unit/common/test_phase6_contracts.py` passes all 26 cases (9 Phase 6 error classes + 17 `sanitize_untrusted` / `PAYLOADS` cases).
- **Skill validator & trace checker:** `tests/unit/skill/test_validate_skill.py` (6 tests) and `tests/unit/skill/test_skill_traces.py` (11 tests across 8 good traces and 3 bad traces) pass.
- **Policy write gating:** `tests/unit/policy/test_gates.py` covers `Capability.PLAYLIST_WRITE` and `PolicyGates.playlist_write_allowed()` (fail-closed unless `POL-04`, `POL-05`, `POL-07`, `POL-08`, and `PLAYLIST_WRITES_ENABLED=true` are all satisfied).
- **Demo F:** `tests/e2e/test_demo_f_prompt_injection.py` verifies the 15-payload corpus sanitization and safe `ApprovalInvalidError` contract; the full e2e flow is skipped pending A's `FixtureWritePlaylistProvider` and B's proposal/confirmation services.

## Remaining Phase 6 gate items

1. Merge A's fixture write provider, operations persistence, executor, and reconciler, plus B's proposal state machine/MRTR/tools and C's constraint filter.
2. Enable and pass Demos A, B, C, D, E, and un-skip Demo F (`test_demo_f_prompt_injection_blocks_unapproved_writes`).
3. Wire `scripts/validate_skill.py` into CI and complete manual Claude Desktop evaluation in `docs/skill_eval.md`.
4. Complete C↔D and A↔B pair reviews and keep `PLAYLIST_WRITES_ENABLED=false` while `POL` gates remain closed.
