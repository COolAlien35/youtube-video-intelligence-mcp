# Phase 7 stage review · Hardening, demos & release (Person D snapshot)

**Gate decision: hold for team integration.** Person D's documentation, governance, change-control, policy-status, and release-evidence artifacts are prepared on top of the Phase 6 stack. Final release sign-off awaits A's retention/recovery/Render deliverables, B's final security review & release tag, and C's Demos A–G, ranking evaluation, and `--strict` RTM pass.

| Owner | Deliverable & Status | Remaining Gate Work |
|---|---|---|
| A | Retention runner (`5m`/`24h`/`7d`/`30d`), `DeletionService`, `RecoveryScan`, `/healthz` & `/readyz`, `render.yaml`, ops runbook | Pending implementation & boundary tests |
| B | `ProposalRepo.expire_due`, `delete_my_data`, final security review, MCP e2e run, `v1.0.0-rc.1` tag | Pending |
| C | Demos A–G e2e tests, `Precision@K`/`NDCG@K` ranking eval, `validate_traceability.py --strict`, coverage report | Pending |
| D | `scripts/check_docs.py`, `scripts/policy_status.py`, `docs/change_control/`, `docs/policy/evidence_requests.md`, `docs/governance/audit.md`, `second-brain/index.md`, `README.md`, `RELEASE_NOTES.md`, `docs/release/evidence.md`, `docs/release/rtm_signoff.md` | Drafted & verified offline (`check_docs.py`, `policy_status` & `docs` unit tests pass) |

## Carry-overs & Risks

- All baseline interpretations (`CR-01`–`CR-12`) are recorded in [`docs/change_control/log.md`](../change_control/log.md) for B's ADR review and team approval.
- Live YouTube API access remains disabled (`YT_INTEL_LIVE_YOUTUBE_ENABLED=false`, `YT_INTEL_PLAYLIST_WRITES_ENABLED=false`) until written `POL-01`–`POL-08` determinations arrive.
