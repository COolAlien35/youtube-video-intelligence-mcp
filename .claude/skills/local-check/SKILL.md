---
name: local-check
description: Verify a contributor checkout before review or a stage demonstration.
---

# local-check

1. From the repo root run `scripts/local_check.sh` (PowerShell uses `scripts/local_check.ps1`). Record lock sync, Ruff lint, format, mypy, pytest and secret-scan outcomes separately.
2. For sync failures, distinguish network or Python errors from a stale lock and route dependency changes to A. For Ruff, inspect the reported rule and location, apply the smallest correction and format affected files. For mypy, follow the first incompatible type to its producer. For pytest, reproduce the failing test by node ID with synthetic fixtures.
3. Re-run the full script after fixes. Never bypass a failing check. Record a skipped local gitleaks scan and verify the CI secret-scan before merge.
4. Run `uv build` and confirm both source and wheel artifacts are produced. Once the server entry point exists, start the documented fixture-backed service locally, invoke one documented read-only fetch with a synthetic ID, verify its result and stop the service. If the entry point or endpoint is absent, mark each step blocked and name the dependency.
5. Report pass, fail, skipped or blocked per step with the revision and evidence. Record the evaluation in the stage review for C’s test documentation.

Distilled source: [Evidence for accepting a deliverable](../../../brain/areas/release-evidence.md).
