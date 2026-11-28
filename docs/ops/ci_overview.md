# CI Overview

## Workflow: `.github/workflows/ci.yml`

**Triggers:** `push` to `main` and `pull_request` targeting `main`.

**Concurrency:** Superseded PR runs are cancelled. Runs on `main` are **never** cancelled, so every commit gets a verdict.

## Jobs

| Job (= check name) | Runs on | What it does | Required |
|---|---|---|---|
| `check` | `ubuntu-latest` | Aggregates all seven validation jobs and fails when a required job fails, is cancelled or is unexpectedly skipped | Stable aggregate required by the repository |
| `lint` | `ubuntu-latest` | `ruff check .` + `ruff format --check .` | ✅ From bootstrap |
| `typecheck` | `ubuntu-latest` | `mypy src scripts` (strict mode) | ✅ From bootstrap |
| `test` | `ubuntu-latest` | `pytest --cov=src` + coverage summary + uploads `coverage.xml` artifact | ✅ Phase 2 (A-6) |
| `test-windows` | `windows-latest` | `pytest` (two developers use Windows) | ✅ From bootstrap (D7) |
| `secret-scan` | `ubuntu-latest` | gitleaks over full history (`fetch-depth: 0`) | ✅ From bootstrap |
| `rtm-check` | `ubuntu-latest` | RTM validator (see below) | ✅ After C's validator merges |
| `pr-title` | `ubuntu-latest` | Conventional Commit PR title check | ✅ After its first PR run (D10) |

### When checks were added to branch protection

1. **After bootstrap push:** `lint`, `typecheck`, `test`, `test-windows`, `secret-scan`
2. **After the first PR:** `pr-title`
3. **After C's validator merges and `rtm-check` runs (not skipping):** `rtm-check`

The repository also expects the aggregate status named `check`. This job runs
after every validation job, even when a dependency fails, so it always reports
a verdict. All seven dependencies must succeed on a pull request. On pushes
and manual runs, only `pr-title` may be skipped because it requires a PR event.

## Coverage Summary (Phase 2, A-6)

The `test` job now runs `pytest --cov=src --cov-report=term-missing --cov-report=xml:coverage.xml`.

- **Job summary:** A markdown table is appended to the GitHub Actions job summary on every run (including failures), so coverage is visible without downloading the artifact.
- **Artifact:** `coverage.xml` is uploaded as a GitHub Actions artifact named `coverage-xml` (retained for the default 90 days) for tooling integration.
- **Non-blocking:** A coverage dip does **not** fail CI — only test failures do. Coverage enforcement (minimum threshold) is deferred to Phase 3 when the codebase stabilises.

## Shared Setup

Every job uses `.github/actions/setup-project/action.yml`, which:
1. Installs the pinned uv (0.11.32) via `astral-sh/setup-uv@v6`
2. Restores the uv cache keyed on `uv.lock`
3. Runs `uv sync --locked`

This makes a stale lockfile fail CI (TQ-14). Setup lives in one place so the jobs can't drift apart.

## `rtm-check` Logic

The `rtm-check` job behaves in three ways:
1. **Validator + RTM CSV exist:** Runs `scripts/validate_traceability.py` ✅
2. **RTM CSV exists but validator doesn't:** **Fails** ❌ — prevents a missing validator from hiding broken work
3. **Neither exists:** Prints a message and passes ⊘ — this is the only case where it skips

## Reading and Fixing a Failing Job

1. Open the **Actions** tab → click the failing workflow run → click the failing job.
2. Expand the failing step to see the error output.
3. Fix the issue locally, verify with `scripts/local_check.sh`, then push.

| Failure | Likely cause | Fix |
|---|---|---|
| `lint` | Ruff rule violation | `uv run ruff check . --fix` then review |
| `lint` (format) | Unformatted code | `uv run ruff format .` |
| `typecheck` | mypy type error | Fix the type annotation or add a `# type: ignore[code]` with justification |
| `test` or `test-windows` | Test failure | Fix the test or the code |
| `secret-scan` | Potential secret in code | Remove the secret; use `FAKE_` prefix for test fixtures |
| `rtm-check` | Validator failed or missing | Check `scripts/validate_traceability.py` and `docs/rtm/requirements_rtm.csv` |
| `pr-title` | PR title doesn't follow Conventional Commits | Rename the PR: `type: description` |

## Action Pinning Policy

| Phase | Pinning method |
|---|---|
| Bootstrap | Version tags (`actions/checkout@v4`, etc.) — keeps the first run unblocked |
| Follow-up PR (`chore/pin-actions`) | Full commit SHA with tag in comment: `@<sha> # v4` |
| Ongoing | Dependabot (`.github/dependabot.yml`) proposes SHA bumps weekly |

**To verify a SHA:** Go to the action's GitHub releases page. Find the release tagged with the version. The commit SHA is shown on the release page.

## Permissions Policy

- **Top-level:** `permissions: contents: read` (least privilege, TQ-28)
- **Per-job:** Widened only where needed (e.g., `secret-scan` uses `GITHUB_TOKEN` for the gitleaks action)
- **Checkout:** `persist-credentials: false` on every checkout, so the job token isn't left in git config
- **Timeouts:** Every job has `timeout-minutes` to prevent hung jobs from blocking the queue

## No Secrets Required

The CI workflow references **no repo secrets**. The gitleaks action reads the built-in `GITHUB_TOKEN`, which is not a repo secret. No YouTube API calls are made.
