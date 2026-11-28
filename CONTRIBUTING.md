# Contributing

## Set up

```sh
git clone https://github.com/COolAlien35/youtube-video-intelligence-mcp.git
cd youtube-video-intelligence-mcp
uv sync --locked
```

Use Python 3.12 and the pinned uv version in the [environment guide](docs/ops/dev_environment.md). Use the lockfile in version control. A owns dependency changes.

## From issue to merge

1. Claim an issue with a testable outcome and affected requirement IDs. Check ownership before editing. For a documentation change, a suitable outcome is “a reviewer can locate evidence for every Phase 1 gate.”
2. Update main with `git switch main` and `git pull --ff-only`. Create a focused branch, e.g. `git switch -c docs/phase1-review`. Use feat, fix, docs, chore, ci or test as the prefix.
3. Stage the intended files and make a Conventional Commit, e.g. `git commit -m "docs: record phase one gate evidence"`. Keep each PR small enough to review one deliverable and its verification together.
4. Run `scripts/local_check.sh` (or the PowerShell equivalent) plus `uv run python scripts/check_docs.py` and `uv run python scripts/validate_skill.py`. Push your branch and use the [PR template](.github/PULL_REQUEST_TEMPLATE.md). Use a Conventional Commit PR title, fill in `Closes #<actual issue number>`, relevant SRS IDs and any AI contribution.
5. Request review from your partner (A ↔ B, C ↔ D). Aim to acknowledge requests within two hours. Describe each blocking finding with its location, impact and expected behavior. Authors respond with the correction or rationale.
6. Resolve conflicts on the feature branch. For a shared or published branch, merge current origin/main and coordinate with coauthors. For a private unpublished branch, rebase on origin/main. Inspect each conflicting hunk with its owner and rerun checks. Obtain fresh approval after substantive edits. Squash-merge via GitHub.

## Failing checks

Open the failing job and expand its first failing step. Reproduce its command from the same commit and locked environment. A passing summary with an inactive validator does not verify traceability. See the [CI job reference](docs/ops/ci_overview.md) and [local-check skill](.claude/skills/local-check/SKILL.md).

## Baseline and phase decisions

Use the [change request template](.github/ISSUE_TEMPLATE/change_request.md) for baseline changes. Include the affected SRS text, ADRs, RTM, tests and owners. Follow Proposed → Under Review → Approved → Implemented → Verified. Record the approval before changing the baseline.

A deliverable is done when its acceptance evidence, relevant tests, linked documentation and traceability updates have passed review and merged. For a phase transition, D assembles the [stage review](docs/stage_reviews/TEMPLATE.md) and the team verifies every gate on main. Begin Phase N+1 only after sign-off.

## Phase 2 working agreements

A owns pyproject.toml and uv.lock. Request a dependency on the Phase 2 dependency requests issue with its package name, purpose and verified licence. Keep test filenames unique across the repository, such as test_common_logging.py. Put tests in tests/unit/<module>/ or tests/integration/<module>/. Mark them explicitly until C’s directory-based markers merge, and mark security-relevant cases with pytest.mark.security. Server, tools and provider APIs are async. Storage and quota are synchronous; async callers run them via anyio.to_thread.run_sync.
