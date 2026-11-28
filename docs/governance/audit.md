# Governance Audit (`DEV-AI-01`–`DEV-AI-30`)

Audit of engineering governance and AI-assisted development controls against [Engineering Governance Specification v1.0](../Engineering_Governance_Specification_v1.0.md).

| ID Range | Control Area | Repository Evidence | Status |
|---|---|---|---|
| `DEV-AI-01`–`05` | Repository setup, branch protection, PR template & CODEOWNERS | [`.github/PULL_REQUEST_TEMPLATE.md`](../../.github/PULL_REQUEST_TEMPLATE.md), [`.github/CODEOWNERS`](../../.github/CODEOWNERS), [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml) | `Implemented` |
| `DEV-AI-06`–`10` | Pinned environment, Ruff, strict mypy, pytest, gitleaks | [`pyproject.toml`](../../pyproject.toml), [`uv.lock`](../../uv.lock), [`.gitleaks.toml`](../../.gitleaks.toml), [`scripts/local_check.sh`](../../scripts/local_check.sh) | `Implemented` |
| `DEV-AI-11`–`15` | Agent instructions, contributor guide, paired reviews (`A↔B`, `C↔D`) | [`AGENTS.md`](../../AGENTS.md), [`CONTRIBUTING.md`](../../CONTRIBUTING.md), [`.claude/skills/local-check/SKILL.md`](../../.claude/skills/local-check/SKILL.md) | `Implemented` |
| `DEV-AI-16`–`20` | Second-brain PARA vault, ingest/refine/query workflow | [`second-brain/README.md`](../../second-brain/README.md), [`second-brain/1-projects/yt-intel-mcp/brain-query-log.md`](../../second-brain/1-projects/yt-intel-mcp/brain-query-log.md) | `Implemented` |
| `DEV-AI-21`–`25` | AI disclosure, source-checked stage reviews, human gate sign-off | [`docs/stage_reviews/phase1_review.md`](../stage_reviews/phase1_review.md), [`docs/stage_reviews/phase3_review.md`](../stage_reviews/phase3_review.md), [`docs/stage_reviews/phase6_review.md`](../stage_reviews/phase6_review.md) | `Implemented` |
| `DEV-AI-26`–`30` | Change control, RTM traceability, docs/skill validation | [`docs/change_control/log.md`](../change_control/log.md), [`scripts/validate_traceability.py`](../../scripts/validate_traceability.py), [`scripts/check_docs.py`](../../scripts/check_docs.py), [`scripts/validate_skill.py`](../../scripts/validate_skill.py) | `Implemented` |
