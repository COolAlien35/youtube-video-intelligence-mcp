# Release Evidence Pack (`v1.0.0-rc.1`)

## Evidence Index

| Area | Artifact / Evidence | Status |
|---|---|---|
| Product & Release | [README](../../README.md) · [Release Notes](../../RELEASE_NOTES.md) · [Docs Index](../index.md) | Prepared |
| Policy & Gates | [Gate Status](../policy/gate_status.md) · [Evidence Requests](../policy/evidence_requests.md) · [Write Gating](../policy/write_gating.md) | All `POL-01`–`08` closed |
| Governance & Change Control | [Governance Audit (`DEV-AI-01`–`30`)](../governance/audit.md) · [Change Control Log](../change_control/log.md) | Prepared (`CR-01`–`12`) |
| Stage Reviews | [Phase 1](../stage_reviews/phase1_review.md) · [Phase 2](../stage_reviews/phase2_review.md) · [Phase 3](../stage_reviews/phase3_review.md) · [Phase 6](../stage_reviews/phase6_review.md) · [Phase 7](../stage_reviews/phase7_review.md) · [Consolidated](../stage_reviews/consolidated_review.md) | Prepared |
| Skill & Trace Eval | [Skill Eval](../skill_eval.md) · [Playlist Workflow](../tools/playlist_workflow.md) | Scripted traces passing; manual client run pending |
| RTM Sign-Off | [RTM Sign-Off](rtm_signoff.md) · [RTM CSV](../rtm/requirements_rtm.csv) | Pending C's `--strict` pass |
| Ops & Security | [Infra Prerequisites](../ops/infra_prerequisites.md) · [Render Secrets & HTTPS](../ops/render_secrets_and_https.md) · [Phase 3 Threat Model](../security/threat_model_phase3.md) | Phase 7 A/B final artifacts pending |

## Running Verification Locally

```bash
scripts/local_check.sh
uv run python scripts/validate_skill.py
uv run python scripts/check_docs.py
uv run python scripts/policy_status.py
uv run pytest tests/unit/skill/ tests/unit/docs/ tests/unit/scripts/ tests/e2e/test_demo_f_prompt_injection.py
```
