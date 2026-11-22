# Phase 1 · Person A: CI, GitHub Actions and Repo Setup Plan (v2)

**Owner:** Person A (DevOps & Backend Lead). Repo owner: `COolAlien35`. This plan assumes you are Person A.
**Repo:** https://github.com/COolAlien35/youtube-video-intelligence-mcp (public, already created)
**Ground truth:** `phase1_person_A.md`, §0 (shared contract) and §1 (A-1 to A-10). Where this plan changes the contract, section 3 says so.
**Starter files:** `bootstrap/` (first push to `main`) and `bootstrap-pr2/` (second PR). Copy them into the repo. This plan doesn't repeat their contents, so it can't drift from them.
**Changes from v1:** listed in `plan_bug_report.md`. v1 is kept as `plan_v1.md`.

---

## 0. Current state and assumptions

- The repo exists, is public, and has default branch `main`. It is believed to be empty. Verify in step 4.1.
- Two team members develop on Windows. Windows support is required, not optional.
- C has not started yet. B and D should have accepted their Write invites. Confirm this.
- Dates are not enforced in this plan. The order of steps matters. Dates will be flagged to the team later.
- **Pinned uv version: `0.11.32`.** Every developer and CI must use this exact version. Install it with the versioned installer:
  - macOS / Linux / Git Bash: `curl -LsSf https://astral.sh/uv/0.11.32/install.sh | sh`
  - Windows PowerShell: `powershell -ExecutionPolicy Bypass -c "irm https://astral.sh/uv/0.11.32/install.ps1 | iex"`
  - Check with `uv --version`.

---

## 1. Blocking items (resolve before the first push)

| # | Item | Owner | Why it blocks |
|---|---|---|---|
| B1 | GitHub handles of B, C and D | All | `CODEOWNERS` needs real handles. Placeholders must not be merged. |
| B2 | B, C and D accept the Write invites | All | Without Write access they can't push branches. |
| B3 | Repo is empty (`git ls-remote` shows no refs) | A | If GitHub created an initial commit, the bootstrap push is rejected. |
| B4 | Everyone has uv 0.11.32 | All | CI and local results must match. |
| B5 | Licence decision (D3) | Team | Not a CI blocker, but a public repo with no licence means all rights are reserved. Decide before anyone outside the team relies on it. |

---

## 2. Definition of done (CI and repo scope)

- [ ] `main` has the bootstrap commit, pushed directly by A (the only direct push in the project)
- [ ] `scripts/local_check.sh` (or `.ps1`) passes on A's machine
- [ ] The first CI run on `main` is green. The checks are: `lint`, `typecheck`, `test`, `test-windows`, `secret-scan`
- [ ] Branch protection is on and tested: B's direct push to `main` is rejected
- [ ] Actions hardening, squash-only merging and security features are set (section 8)
- [ ] `.gitleaks.toml` is merged and verified (section 9)
- [ ] Labels and Phase 1 issues exist (section 10)
- [ ] PR template, SECURITY.md and CODEOWNERS are merged, PR 2 (section 11)
- [ ] Ops docs are merged, PR 3 (section 12)
- [ ] 3 ingest notes are merged, PR 4 (section 13)
- [ ] `rtm-check` runs (is not skipping) and is required, after C's validator merges (section 15)
- [ ] "Repo ready" and the clone URL are posted in the group chat

---

## 3. Decisions

Status: DONE = decided and implemented in the starter files. ADOPTED = recommended and included. OPEN = the team must decide.

| # | Decision | Status | Where it lands |
|---|---|---|---|
| D1 | Repo is **public** | DONE | Free branch protection, secret scanning, push protection and CodeQL on a public repo |
| D2 | Owner is the personal account `COolAlien35` | DONE | gitleaks action needs no licence key for personal repos |
| D3 | Licence | **OPEN** | Public repo with no licence = all rights reserved. Options: MIT, Apache-2.0, or none by choice. Team decides. |
| D4 | Windows is supported | DONE | `scripts/local_check.ps1` is required; `test-windows` CI job |
| D5 | Action pinning | DONE (two phases) | Bootstrap uses version tags so the first run isn't blocked. A follow-up PR pins to full SHAs with the tag in a comment. Dependabot then keeps SHAs current. |
| D6 | Dependabot for GitHub Actions | ADOPTED | `.github/dependabot.yml` |
| D7 | Extra CI job `test-windows` | ADOPTED. **Changes the contract.** | `phase1_person_A.md` §0.2 lists four required checks. This adds a fifth, `test-windows`. Announce it in the group chat. |
| D8 | Pre-commit hooks | ADOPTED (recommended) | `.pre-commit-config.yaml`. The gitleaks hook needs gitleaks installed locally. |
| D9 | CodeQL (Python) | ADOPTED | Enable as **default setup** in the repo settings. No workflow file, so nothing to maintain. |
| D10 | `pr-title` check (Conventional Commit PR titles) | ADOPTED | Squash merge uses the PR title, so the title is the commit message. Required once it has run on a PR. |
| D11 | Ingest notes route to C through the `/second-brain/` CODEOWNERS rule | OPEN (accepted for now) | Revisit once C starts. Ingest notes are written by everyone, but CODEOWNERS can only route by path. |
| D12 | Issue templates stay as `.md` files | DECIDED | Matches the contract (A-6). YAML issue forms are an option later. |

---

## 4. Repo setup and first push (bootstrap, direct push to `main`)

**4.1 Confirm the repo is empty.**
```bash
git ls-remote https://github.com/COolAlien35/youtube-video-intelligence-mcp.git
```
This should print nothing. If it prints refs, stop. Don't force-push. Tell the team and inspect the commit first.

**4.2 Clone.**
```bash
git clone https://github.com/COolAlien35/youtube-video-intelligence-mcp.git
cd youtube-video-intelligence-mcp
```
Git will warn that the repository is empty. That is expected.

**4.3 Copy the bootstrap files into the clone.** Copy `bootstrap/` only. Don't copy `bootstrap-pr2/` yet.
```bash
cp -R /path/to/bootstrap/. .
```
`cp -R dir/. .` includes dotfiles (`.github`, `.gitignore`, `.gitattributes`, and so on). Check with `ls -la`.

**4.4 Generate the lockfile.** This needs network access.
```bash
uv lock
```
Commit `uv.lock`. It is required for `uv sync --locked`.

**4.5 Run the local checks** (section 5). Everything must pass before you push.

**4.6 Stage everything and set the executable bit in git.**
```bash
git add -A
git update-index --chmod=+x scripts/local_check.sh
git ls-files -s scripts/local_check.sh
```
The last command must show `100755`. This works on every OS, including Windows, where the file system can't set the bit. The bit must be in git's index, not on disk.

**4.7 Check line endings.**
```bash
git ls-files --eol scripts/local_check.sh
```
It must show `i/lf`. (`file` is not on Windows. `git ls-files --eol` works everywhere.)

**4.8 Commit and push.**
```bash
git commit -m "chore: bootstrap repo with tooling and CI"
git push -u origin main
```

**4.9 Watch the first run.** Open the Actions tab. Six jobs run on push: `lint`, `typecheck`, `test`, `test-windows`, `secret-scan`, `rtm-check`. `pr-title` only runs on pull requests.

**4.10 If anything is red,** fix it with another direct commit to `main`. Direct pushes are allowed until branch protection is on (section 8.4). After that, every change goes through a PR.

**4.11 Post "repo ready"** and the list of check names in the group chat (section 18).

---

## 5. Local checks

Run the same five checks CI runs, in the same order:

- Git Bash, macOS or Linux: `scripts/local_check.sh`
- Windows PowerShell: `powershell -ExecutionPolicy Bypass -File scripts\local_check.ps1`

The Bash script stops at the first failure and prints which check failed. The PowerShell script checks `$LASTEXITCODE` after every native command, because PowerShell does not stop on a failing native command by default.

Known issues to check first:

- **mypy on an empty directory fails.** `scripts/__init__.py` in the bootstrap gives mypy a file to check.
- **`uv sync --locked` fails** when `uv.lock` doesn't match `pyproject.toml`. Run `uv lock` and commit the result.
- **`ruff format --check` fails.** Run `uv run ruff format .`, then check again.
- **`S101` (assert) fires in tests.** Already ignored for `tests/**` in `pyproject.toml`.
- **PowerShell refuses to run the script.** Use the `-ExecutionPolicy Bypass` form above. Don't change the machine-wide policy.
- **gitleaks is optional locally.** The check is skipped with a message if it isn't installed. CI always scans.

---

## 6. CI (`.github/workflows/ci.yml`, in `bootstrap/`)

| Job (= required check name) | Runs on | What it does | Required |
|---|---|---|---|
| `lint` | ubuntu | `ruff check`, `ruff format --check` | Yes, from bootstrap |
| `typecheck` | ubuntu | `mypy src scripts` (strict) | Yes, from bootstrap |
| `test` | ubuntu | `pytest` | Yes, from bootstrap |
| `test-windows` | windows | `pytest` (two developers use Windows) | Yes, from bootstrap (D7) |
| `secret-scan` | ubuntu | gitleaks over full history | Yes, from bootstrap |
| `rtm-check` | ubuntu | RTM validator (see below) | Required after C's validator merges |
| `pr-title` | ubuntu, PRs only | Conventional Commit PR title | Required after its first PR run (D10) |

**Shared setup.** Every job uses `.github/actions/setup-project`. It installs the pinned uv (0.11.32), restores the uv cache keyed on `uv.lock`, and runs `uv sync --locked`. That makes a stale lockfile fail in CI, as TQ-14 requires. Setup lives in one place, so the jobs can't drift apart.

**`rtm-check` logic.** It behaves three ways:
- If `scripts/validate_traceability.py` exists, it runs the validator.
- If the RTM CSV exists but the validator doesn't, it **fails**. This stops a missing validator from hiding broken work.
- If neither exists, it prints a message and passes. This is the only case where it skips.

**Design rules built into `ci.yml`:**
- Job IDs and `name:` fields are identical, so branch protection's check names are stable.
- Top-level `permissions: contents: read`. A job widens its permissions only where it needs to.
- `persist-credentials: false` on every checkout, so the job token isn't left in the git config.
- `timeout-minutes` on every job, so a hung job can't block the queue.
- Concurrency cancels superseded **PR** runs only. It never cancels runs on `main`, so every commit on `main` gets a verdict.
- No YouTube calls and no repo secrets. The gitleaks action reads the built-in `GITHUB_TOKEN`, which is not a repo secret. Say this in review so it isn't a surprise.

**Action pinning policy (D5).**
- Bootstrap: version tags (`actions/checkout@v4`, and so on). This keeps the first run unblocked.
- Follow-up PR (section 15): replace each `@vN` in `ci.yml` and `setup-project/action.yml` with the full commit SHA, and put the tag in a comment, e.g. `@<sha> # v4`. Verify each SHA against the action's release page.
- Dependabot (`dependabot.yml`) then proposes SHA bumps weekly.
- Record this policy in `docs/ops/ci_overview.md`.

---

## 7. Required checks: what appears when

Branch protection only lists checks that have run at least once. Add them in this order:

1. After the bootstrap push: `lint`, `typecheck`, `test`, `test-windows`, `secret-scan`
2. After the first PR runs: `pr-title`
3. After C's validator merges and `rtm-check` runs for real (not skipping): `rtm-check`

---

## 8. GitHub settings

Do these in order. Section 8.1 comes before the bootstrap push. Section 8.4 comes after the first green run.

**8.1 Settings → Actions → General (before the push).**
- **Actions permissions:** "Allow select actions and reusable workflows". Allow: `actions/*`, `astral-sh/setup-uv@*`, `gitleaks/gitleaks-action@*`, `amannn/action-semantic-pull-request@*`. Tick "Allow actions created by GitHub".
  - If CodeQL default setup later reports a blocked action, add `github/codeql-action/*`.
- **Workflow permissions:** "Read repository contents and packages permissions" (the read-only default). Leave "Allow GitHub Actions to create and approve pull requests" **unticked**.
- **Fork pull request workflows from outside collaborators:** "Require approval for all outside collaborators".

**8.2 Settings → General → Pull Requests.**
- Allow **squash merging only**. Untick merge commits and rebase merging.
- Tick "Default to pull request title for squash commit messages". This makes the `pr-title` check meaningful.
- Tick "Automatically delete head branches".

**8.3 Settings → Code security.**
- Dependabot alerts: on. Dependabot security updates: on.
- Secret scanning: on. Push protection: on. Push protection blocks real-looking secrets from reaching GitHub even if gitleaks isn't run locally.
- Private vulnerability reporting: on. `SECURITY.md` (PR 2) points to it.
- CodeQL: **default setup**, language Python. Don't add a workflow file.

**8.4 Branch protection for `main`** (after the first green run). Use a branch protection rule or a ruleset. Either works. Settings:
- Require a pull request before merging, with **1 approval**
- Dismiss stale approvals when new commits are pushed
- Require status checks to pass: `lint`, `typecheck`, `test`, `test-windows`, `secret-scan`. Add `pr-title` and `rtm-check` later (section 7).
- Require branches to be up to date before merging
- Require conversation resolution before merging
- Block force pushes and deletions
- Include administrators
- **Do not** enable "Require review from Code Owners". It would stall PRs.

**8.5 Prove it works.** Ask B to push directly to `main`. The push must be rejected. Post the result in the group chat.

---

## 9. gitleaks (`.gitleaks.toml`, in `bootstrap/`)

- The config extends gitleaks' default rules with `[extend] useDefault = true`. It doesn't replace them.
- The only allowlist is a regex for clearly fake tokens: `FAKE_` followed by letters, digits, `_` or `-`. Never allowlist paths, because fixtures must still be scanned.
- **Verify locally in a throwaway repo outside the project.** Do not push test secrets anywhere, including this repo, because push protection will block them and they are a bad habit anyway.
  1. Put `FAKE_abcdef12345678` in a file and commit it. gitleaks should report nothing.
  2. Put a fake token in the GitHub format (`ghp_` followed by 36 random characters) in a file and commit it. gitleaks should report it.
  3. Delete the throwaway repo.
- Run locally with `gitleaks git --redact` (`--redact` keeps secrets out of the terminal output).

---

## 10. Labels, milestones and issues

Run these from Git Bash or macOS terminal, with the `gh` CLI logged in as `COolAlien35`:

```bash
REPO=COolAlien35/youtube-video-intelligence-mcp
for l in phase:1 phase:2 phase:3 phase:4 phase:5 phase:6 phase:7 \
  type:feat type:fix type:docs type:chore type:ci type:test type:decision type:change-request \
  area:devops area:backend area:auth area:testing area:docs area:process blocked needs-review; do
  gh label create "$l" --repo "$REPO" --force
done

for m in "Phase 1" "Phase 2" "Phase 3" "Phase 4" "Phase 5" "Phase 6" "Phase 7"; do
  gh api "repos/$REPO/milestones" -f title="$m"
done
```

`--force` updates a label that already exists. Due dates are not set, because the team isn't tracking dates for now.

**Phase 1 issues** (create after B, C and D's handles are known, so you can assign them):
- **A:** bootstrap and tooling · CI skeleton · branch protection · gitleaks config · templates and CODEOWNERS · ops docs · ingest notes (A)
- **B:** ADR-01 to 11 · architecture docs · ingest notes (B)
- **C:** RTM CSV · `validate_traceability.py` and tests · test strategy and fixture policy · ingest notes (C)
- **D:** governance spec · `AGENTS.md` · `CONTRIBUTING.md` · local-check skill · second-brain scaffold · brain-refine and brain-query · ingest notes (D) · stage review
- **Shared:** "Phase 1 stage review inputs" and "Phase 1 gate"

Optional: a GitHub Projects board with columns Todo, In progress, In review and Done.

---

## 11. Templates, CODEOWNERS and SECURITY (PR 2)

Branch: `chore/github-templates`. Reviewer: B.
```bash
git switch -c chore/github-templates
cp -R /path/to/bootstrap-pr2/. .
```

Files in `bootstrap-pr2/.github/`:
- `PULL_REQUEST_TEMPLATE.md`: summary, linked issue, SRS IDs, type, local check, tests, docs and RTM, no-secrets confirmation, AI-assistance disclosure, baseline impact.
- `SECURITY.md`: private vulnerability reporting. Points to the Security tab.
- `CODEOWNERS`: review routing (below).

Still to write in this PR: `.github/ISSUE_TEMPLATE/task.md`, `bug.md` and `change_request.md`. The change request template must have: description, impact assessment, and affected SRS, ADR and RTM items. This matches SRS §10.

**CODEOWNERS rules:**
- Review partners are A↔B and C↔D. A's paths route to B, B's to A, C's to D, and D's to C.
- **Last matching pattern wins.** Broad rules come first, specific rules after. The starter file already follows this order.
- **Replace `@B_HANDLE`, `@C_HANDLE` and `@D_HANDLE` before merging PR 2.** Placeholders must never reach `main`.
- `@COolAlien35` (you) is already filled in. It is the owner for the B-owned ADR and architecture paths, which route to A.
- Ingest notes under `second-brain/3-resources/ingest/` fall under the `/second-brain/` rule and route to C (D11). This is accepted for now.
- Don't enable "Require review from Code Owners" (section 8.4).

---

## 12. Ops docs (`docs/ops/`, PR 3)

Branch: `docs/ops-docs`. Reviewer: B.

- **`dev_environment.md`:** install uv 0.11.32 (section 0). Python 3.12 is installed automatically by uv from `.python-version`. Windows notes: install Git for Windows (it includes Git Bash), the PowerShell command with `-ExecutionPolicy Bypass`, and that line endings are handled by `.gitattributes`. Install gitleaks: `brew install gitleaks` on macOS. On Windows, use `winget install gitleaks.gitleaks` and check the package ID first. Run `uv run pre-commit install` once per clone. Common errors: `uv.lock` out of date, and the executable-bit fix from step 4.6.
- **`ci_overview.md`:** the job table (section 6), which checks are required and when they were added, how to read and fix a failing job, the pinning policy (section 6), the permissions policy, and how `rtm-check` is wired.
- **`infra_prerequisites.md`:** a checklist only. **Create nothing yet.** It covers:
  - A Render web service with a persistent disk at `/var/data`. Persistent disks need a paid instance type. Confirm the plan and price.
  - A Supabase project in `ap-southeast-1`.
  - Exactly **one** Google Cloud project (ADR-05). Extra projects for extra quota are prohibited.
  - Where each secret lives: Render environment variables or GitHub secrets, never git.
  - Who owns each account.
  - An explicit statement that no API keys are created in Phase 1 and the YouTube Data API is not enabled.

---

## 13. Brain-ingest notes (PR 4)

Branch: `docs/ingest-notes-a`. Reviewer: B. Files in `second-brain/3-resources/ingest/`:
1. `ingest_A_render-persistent-disks.md`: Render persistent disks and single-instance behaviour
2. `ingest_A_gha-permissions-uv-cache.md`: GitHub Actions least-privilege permissions and uv caching
3. `ingest_A_sqlite-wal.md`: SQLite WAL mode and concurrent writers

Use the §0.6 headings: Source · Ingested by / date · Summary · Key facts (each with a source) · Relevance (SRS IDs) · Open questions / risks · Links. Use official docs as sources. Write in your own words. Don't paste copyrighted text.

---

## 14. Reviews you owe

- **B's PRs** (ADRs and architecture docs). Focus on ADR-02, 04, 07, 09 and 10. Check that the data model works on SQLite WAL, and that the package name matches `yt_intel`.
- Review within about 2 hours of a PR being opened, so nothing stalls.
- B reviews your PRs too. Nothing merges without one approval from the review partner.

---

## 15. Follow-ups (after the bootstrap is green)

1. **SHA pinning PR** (`chore/pin-actions`): pin `ci.yml` and `setup-project/action.yml` to full SHAs (section 6).
2. **Add `pr-title` to required checks** after the first PR has run it (section 7).
3. **`rtm-check`:** once C's validator merges, confirm the job log says the validator ran, not that it skipped. Then add `rtm-check` to required checks and update `ci_overview.md`.
4. **Recommended later:** a workflow security linter such as `zizmor`, run after the SHA pinning PR, so it doesn't fail on tag pins. Add it as a dev dependency and run it in `lint`.
5. **Before the Phase 1 gate:** re-check that CI is green on `main`, branch protection is active, and gitleaks is clean across the history.

---

## 16. Order of work

| Step | Task | Blocks | Depends on |
|---|---|---|---|
| 1 | Confirm B1 to B5 (section 1) | Everything | Nothing |
| 2 | Actions settings (8.1) and PR settings (8.2) and security settings (8.3) | Safe CI | Step 1 |
| 3 | Clone, copy `bootstrap/`, `uv lock`, local checks (section 4 to 5) | Push | Step 2 |
| 4 | Push bootstrap, get CI green (section 4.8 to 4.10) | B, C, D | Step 3 |
| 5 | Post "repo ready" | B, C, D | Step 4 |
| 6 | Branch protection and B's push test (8.4 and 8.5) | Safe PRs | Step 4 |
| 7 | Labels, milestones (section 10) | Planning | Step 5 |
| 8 | PR 2: templates, SECURITY.md, CODEOWNERS (section 11). Gitleaks config tested (section 9) | Review routing | Step 6 |
| 9 | PR 3: ops docs (section 12) | Phase 1 gate | Step 6 |
| 10 | PR 4: ingest notes (section 13) | Phase 1 gate | Step 6 |
| 11 | Review B's PRs (section 14) | Their merges | Their PRs |
| 12 | SHA pinning PR, then `pr-title` required (section 15) | Pinning policy | Step 4 |
| 13 | `rtm-check` required (section 15) | Phase 1 gate | C's validator |

Steps 8 to 10 are separate PRs with one deliverable each, as the Phase 1 PR plan requires. Steps 7 and 8 can run in parallel.

---

## 17. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Repo isn't empty (GitHub initialised it) | Bootstrap push is rejected | Step 4.1 check |
| A missing Actions permission in 8.1 | Bootstrap CI fails with a permissions error | Set 8.1 before the push. If a job is blocked, add the named action to the allow list. |
| First CI run red | Nobody can merge | Fix on `main` directly, while protection is off (step 4.10) |
| Lockfile missing or stale | `uv sync --locked` fails everywhere | Step 4.4 |
| Developers on different uv versions | Different lint or type results | uv 0.11.32 everywhere (section 0) |
| Windows executable bit missing | `local_check.sh` can't run on macOS/Linux clones | Step 4.6 uses `git update-index` |
| Placeholder handles in CODEOWNERS | Review routing breaks, or the file is malformed | B1, and the PR 2 rule against placeholders |
| gitleaks action asks for a licence | Secret scan blocked | Public repo (D1). Fallback is the binary in section 9. |
| C hasn't started | `rtm-check` skips for now. Ingest notes route to C with no one to review them. | The guarded step. D11. Revisit when C starts. |
| Licence never chosen | Public repo stays all-rights-reserved | D3. Decide before inviting outside contributors. |
| Render persistent disk is paid only | Unbudgeted cost | Confirm the plan and price in `infra_prerequisites.md` |

---

## 18. Group chat messages

**Repo ready (after step 4):**
> Repo is ready: https://github.com/COolAlien35/youtube-video-intelligence-mcp. CI checks: lint, typecheck, test, test-windows, secret-scan, rtm-check (skipping until C's validator lands). Please accept the Write invite and install uv 0.11.32 (`uv --version` must print 0.11.32). Branch names: `<type>/<slug>`. PR titles: Conventional Commits. PRs need 1 approval from your review partner (A↔B, C↔D).

**Decisions still needed:**
> Two decisions needed: (1) Licence for the repo: MIT, Apache-2.0, or none? (2) Confirm the Windows setup: Git for Windows is installed, and you can run `scripts\local_check.ps1`.

**Protection on:**
> Branch protection is on for `main`. Direct pushes are blocked. B, please try a direct push to confirm the rejection.

**`test-windows` added (D7):**
> A new required CI check, `test-windows`, runs the test suite on Windows. This is in addition to the four checks in the Phase 1 plan.

---

## 19. Open decisions and questions

- **D3 licence:** OPEN.
- **D11 ingest routing:** accepted for now. Revisit when C starts.
- **B1 handles:** needed for CODEOWNERS.
- **Confirm you are Person A.** The plan assumes you are.
- **C's zero-config requirement:** C must be able to add files under `scripts/` and `tests/` without touching config. Confirm this with C once C starts.

---

## 20. Unverified items

These were not checked against a live system when this plan was written. Verify each one before relying on it.

- **Lint, typecheck and tests were not run.** The sandbox has no network access, so ruff and mypy couldn't be installed. Run `scripts/local_check.sh` on a real machine. Expect small fixes.
- **The PowerShell script was not run.** It was reviewed by reading, not executed.
- **gitleaks flags** (`git --redact`, `--no-banner`, and `--pre-commit --staged`) match the version I know of. Check with `gitleaks git --help` after installing.
- **Action versions and inputs** (`actions/checkout@v4`, `astral-sh/setup-uv@v6` with its `version` and `python-version` inputs, `gitleaks/gitleaks-action@v2`, `amannn/action-semantic-pull-request@v5`) should be checked against each action's current README before the SHA pinning PR.
- **uv installer URLs** for version 0.11.32 should be tested once on a Windows machine.
- **GitHub settings labels** change over time. Check the names against the live Settings pages.
- **The winget package ID** for gitleaks should be checked before it goes into `dev_environment.md`.
