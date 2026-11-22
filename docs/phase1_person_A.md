# Phase 1 — Person A · DevOps & Backend Lead

> **Your phase in one line:** stand up the repo, tooling, CI and project tracker so the other three can merge safely. You go first — your CP1 unblocks everyone.

<!-- SHARED:START -->
## 0. Shared contract (identical in all four Phase 1 files)

**Phase 1 — Foundation & Governance** · Fri 20 Nov → Sat 21 Nov 2026 · SRS refs: §8, §9 (TQ-14–18, TQ-35, TQ-36), DEV-AI-01–30

### 0.1 Roles
| Person | Role this phase | Main outputs |
|---|---|---|
| **A** | DevOps & Backend lead | Repo, tooling, CI, branch protection, issue tracker, `.github/`, ops docs |
| **B** | Architecture & Backend/Auth | ADR-01–11, architecture contracts (module map, data model, error model) |
| **C** | QA & Traceability | RTM CSV, `validate_traceability.py`, test strategy, fixture policy |
| **D** | Process, Governance & Docs | Governance spec, `AGENTS.md`, `CONTRIBUTING.md`, local-check skill, second brain, stage review |

### 0.2 Fixed conventions (decided now so nobody waits on anybody)
- Repo `youtube-video-intelligence-mcp`, default branch `main`. Python 3.12, uv, `src/` layout, package `src/yt_intel/`.
- Local checks (CI runs the same): `uv sync --locked` · `uv run ruff check .` · `uv run ruff format --check .` · `uv run mypy src scripts` · `uv run pytest` · all-in-one: `scripts/local_check.sh`.
- CI job names / required checks: `lint`, `typecheck`, `test`, `secret-scan`. `rtm-check` joins the required list once C's script is merged.
- pytest markers: `unit`, `integration`, `e2e`, `security`.
- Branches: `<type>/<slug>`, type is one of `feat|fix|docs|chore|ci|test` (e.g. `docs/adr-baseline`). Commits: Conventional Commits (`docs: add ADR-01..11`).
- PRs: one deliverable per PR, squash merge, `Closes #<issue>` plus SRS IDs in the description, 1 approval from your review partner. **Review pairs: A↔B, C↔D.** Review within ~2 hours so nothing stalls.
- No direct pushes to `main` — the only exception is A's one-time bootstrap commit.
- Phase 1 adds **no runtime dependencies** and makes **no YouTube API calls** (POL-01–08 gates stay closed). Never commit secrets, tokens or real user data.
- If a fixed convention turns out to be wrong, say so in the group chat before changing it.

### 0.3 File ownership — the conflict map
| Owner | Paths (only the owner edits these in Phase 1) |
|---|---|
| **A** | `README.md`, `.gitignore`, `.python-version`, `pyproject.toml`, `uv.lock`, `.env.example`, `.gitleaks.toml`, `.github/**` (workflows, PR/issue templates, CODEOWNERS), `src/yt_intel/__init__.py`, `tests/test_smoke.py`, `scripts/local_check.sh`, `docs/SRS_v1.0.docx`, `docs/ops/**`, GitHub repo settings, labels/milestones/issues |
| **B** | `docs/Architecture_Decision_Records_v1.0.md`, `docs/architecture/**` |
| **C** | `docs/rtm/**`, `docs/testing/**`, `scripts/validate_traceability.py`, `tests/test_validate_traceability.py`, `tests/fixtures/README.md` |
| **D** | `AGENTS.md`, `CONTRIBUTING.md`, `docs/Engineering_Governance_Specification_v1.0.md`, `docs/stage_reviews/**`, `.claude/skills/local-check/**`, `second-brain/**` (scaffold, templates, index, refined notes, query log) |
| **Everyone** | Own ingest notes only: `second-brain/3-resources/ingest/ingest_<person>_<slug>.md` (unique filenames, so no collisions) |

Need a change in someone else's file? Comment on their issue or PR — don't edit it. Dependencies (`pyproject.toml`, `uv.lock`) belong to A; ask A.

### 0.4 Checkpoints (suggested, IST)
| | When | What must be true |
|---|---|---|
| **CP1** | Fri ~23:00 | A has pushed the bootstrap commit, invited everyone and posted "repo ready". Until then: draft locally, don't sit idle. |
| **CP2** | Sat ~13:00 | Branch protection on; labels, milestones and Phase 1 issues exist; every person has at least one PR open. |
| **CP3** | Sat ~19:00 | All deliverable PRs merged; at least 10 ingest notes on `main`. |
| **CP4** | Sat ~21:00 | D has run brain-refine and brain-query and compiled the stage review; team signs off the gate below. |

### 0.5 Phase 1 gate (all must be true before Phase 2 starts)
- [ ] CI green on `main`; branch protection active; at least 1 human review enforced
- [ ] `docs/rtm/requirements_rtm.csv` validates (`rtm-check` green)
- [ ] ADR-01–11, governance spec (DEV-AI-01–30), `AGENTS.md`, `CONTRIBUTING.md` merged
- [ ] At least 10 brain-ingest notes merged; brain-refine and brain-query demonstrated once
- [ ] `docs/stage_reviews/phase1_review.md` merged
- [ ] No secrets anywhere in repo history (gitleaks clean)

### 0.6 Ingest note format
Each person writes brain-ingest notes (your count and topics are in your section). Use these headings: **Source** · **Ingested by / date** · **Summary** (your own words, 5–10 lines) · **Key facts** (each with its source) · **Relevance** (SRS IDs) · **Open questions / risks** · **Links** (`[[wiki links]]`). D's template in `second-brain/_templates/` will match; if it isn't merged yet, use this list. Never paste copyrighted text — summarize and link.
<!-- SHARED:END -->

## 1. Your deliverables

### A-1 · Repo + bootstrap commit — BLOCKS B, C, D (target: CP1)
1. Collect everyone's GitHub username in the group chat. Create `youtube-video-intelligence-mcp`; invite B, C, D with **Write** access.
2. Push **one bootstrap commit** directly to `main` (the only direct push in the project) containing:
   - `pyproject.toml` — name `yt-intel`, `requires-python = ">=3.12,<3.13"`, `src` layout with a build backend of your choice. **Dev dependency group only**: ruff, mypy, pytest (pytest-cov optional). Configure:
     - Ruff: sensible line length, rule sets at least `E, F, I, B, UP, S`.
     - mypy: strict on `src` and `scripts`.
     - pytest: `testpaths = ["tests"]`, `--strict-markers`, markers `unit`, `integration`, `e2e`, `security`.
     - Make sure C can add files under `scripts/` and `tests/` with zero config changes.
   - `uv.lock` (committed), `.python-version` (3.12).
   - `.gitignore` — Python/uv/IDE, `.env`, `*.sqlite*`, `*.db`, caches, `var/`. Do **not** ignore `docs/` or `second-brain/`.
   - `.env.example` — variable names with empty values only; comment that real values live in Render/GitHub secrets, never in git.
   - `README.md` stub — one-paragraph purpose (SRS §1.1), status line "Live YouTube API access is disabled until POL-01–08 gates clear", quickstart (the §0.2 commands), links to `docs/`.
   - `src/yt_intel/__init__.py` (with `__version__`) and `py.typed`; `tests/test_smoke.py` (marker `unit`) importing the package.
   - `scripts/local_check.sh` — runs the five §0.2 commands in order, fails fast, prints a clear pass/fail summary, executable bit set. Ask the team's OS; if anyone is on Windows, add an equivalent PowerShell script.
   - `docs/SRS_v1.0.docx` — copy of the SRS baseline.
   - `.github/workflows/ci.yml` (see A-2).
3. Verify: `uv sync --locked && scripts/local_check.sh` passes locally and the first CI run on `main` is green (that run creates the check names branch protection needs).
4. Post "repo ready" + clone URL in the group chat.

### A-2 · CI skeleton (`.github/workflows/ci.yml`, part of the bootstrap commit)
- Triggers: `pull_request` and `push` to `main`; `concurrency` cancels superseded runs.
- Top-level `permissions: contents: read` (TQ-28). No secrets referenced. No YouTube calls; tests run on synthetic fixtures only (TQ-5).
- Jobs, with **exactly** these names: `lint` (ruff check + ruff format --check), `typecheck` (mypy src scripts), `test` (pytest), `secret-scan` (gitleaks over full history, `fetch-depth: 0`), `rtm-check`.
- Setup: Python 3.12 via `astral-sh/setup-uv` with caching; `uv sync --locked` so a stale lockfile fails CI (TQ-14).
- Pin third-party actions to a version tag at minimum (full-SHA pin preferred); record the policy in `docs/ops/ci_overview.md`.
- `rtm-check` must not fail before C's script exists, so use a guarded step:
  ```yaml
  - name: Validate RTM (skips until scripts/validate_traceability.py exists)
    run: |
      if [ -f scripts/validate_traceability.py ]; then
        uv run python scripts/validate_traceability.py
      else
        echo "RTM validator not present yet - skipping"
      fi
  ```
- Check the gitleaks action's current licensing rules: it can require a license key for organization-owned repos. If that applies, install the gitleaks binary and run `gitleaks detect --redact` instead.

### A-3 · Branch protection and repo settings (after the first green run on `main`; target CP2)
- Protect `main`: require PR, 1 approval, dismiss stale approvals on new commits, require status checks `lint`, `typecheck`, `test`, `secret-scan` (branch up to date), require conversation resolution, block force-push and deletion, include administrators.
- Squash-merge only; auto-delete head branches.
- Enable secret scanning / push protection if the plan allows.
- **Plan check:** branch protection on *private* repos may need a paid GitHub plan. If you're on Free, either make the repo public (fine — nothing sensitive is ever committed) or use a Pro/Student plan. Decide at CP1 and tell the team.
- Prove it works: ask B to attempt a direct push to `main` (must be rejected).

### A-4 · `.gitleaks.toml`
Extend the default ruleset. If synthetic fixtures need allowlisting, allowlist by **clearly fake token pattern** (e.g. a `FAKE_` prefix), never by whole directory — fixtures must still be scanned. Verify detection locally in a throwaway repo; don't push test secrets.

### A-5 · Tracker setup
- **Labels:** `phase:1`…`phase:7`; `type:feat|fix|docs|chore|ci|test|decision|change-request`; `area:devops|backend|auth|testing|docs|process`; `blocked`; `needs-review`.
- **Milestones (due dates):** Phase 1 – 21 Nov, Phase 2 – 23 Nov, Phase 3 – 24 Nov, Phase 4 – 26 Nov, Phase 5 – 27 Nov, Phase 6 – 28 Nov, Phase 7 – 30 Nov.
- **Phase 1 issues** (assign owners, milestone Phase 1; script with `gh` if you like):
  - A: bootstrap + tooling · CI skeleton · branch protection · gitleaks config · templates + CODEOWNERS · ops docs · ingest notes (A)
  - B: ADR-01–11 · architecture docs (module map, data model, error model) · ingest notes (B)
  - C: RTM CSV · `validate_traceability.py` + tests · test strategy + fixture policy · ingest notes (C)
  - D: governance spec · `AGENTS.md` · `CONTRIBUTING.md` · local-check skill · second-brain scaffold · brain-refine + brain-query · ingest notes (D) · stage review
  - Shared: "Phase 1 stage review inputs" (everyone comments here) and "Phase 1 gate".
- Optional: a GitHub Projects board (Todo / In progress / In review / Done).

### A-6 · `.github/` templates and CODEOWNERS
- `PULL_REQUEST_TEMPLATE.md` checklist: summary · linked issue · SRS IDs · type · `scripts/local_check.sh` passed · tests added/updated · docs/RTM updated · no secrets / no real user data / no live API calls · AI-assistance disclosure (tool, what it did, human reviewed) · baseline impact? (link change request if yes).
- `ISSUE_TEMPLATE/`: `task.md`, `bug.md`, `change_request.md` (change request fields: description, impact assessment, affected SRS/ADR/RTM items — matches the SRS §10 change-control flow).
- `CODEOWNERS`: map each §0.3 path group to its **review partner** (A-owned → B, B-owned → A, C-owned → D, D-owned → C) so reviews are auto-requested. Add a comment saying so. Do **not** enable "require review from Code Owners".
- *Needs:* everyone's GitHub handles (collected in A-1).

### A-7 · Ops docs (`docs/ops/`)
- `dev_environment.md` — install uv + Python 3.12, clone, run checks, common problems; macOS/Linux/Windows notes.
- `ci_overview.md` — what each job does, which are required, how to read and fix failures, action-pinning and permissions policy, how `rtm-check` is wired.
- `infra_prerequisites.md` — checklist only, **create nothing yet**: Render service with persistent disk at `/var/data` (verify the plan/price that supports disks), Supabase project in ap-southeast-1, exactly **one** Google Cloud project (ADR-05; extra projects for quota are prohibited), where each secret will live (Render env / GitHub secrets, never git), who owns each account. State explicitly: no API keys created and YouTube Data API not enabled in Phase 1.

### A-8 · Brain-ingest notes (3)
`second-brain/3-resources/ingest/ingest_A_<slug>.md` on: (1) Render persistent disks and single-instance behaviour, (2) GitHub Actions least-privilege permissions and uv caching in CI, (3) SQLite WAL mode and concurrent writers. Format: §0.6. Use official docs as sources.

### A-9 · Reviews you owe
B's PRs (ADRs + architecture docs). Focus on ADR-02, 04, 07, 09, 10; check the data model is workable on SQLite WAL and that the package name matches `yt_intel`.

### A-10 · Follow-ups after others merge
- When C's validator lands: confirm `rtm-check` actually runs (not skipped), then add it to required checks and update `ci_overview.md`.
- Before CP4: re-verify gate items "CI green / protection active" and "gitleaks clean".

## 2. Dependencies

| You need | From | Blocking? | Workaround |
|---|---|---|---|
| GitHub usernames | B, C, D | Yes (invites, CODEOWNERS) | Ask in the group chat right now |
| Ingest template | D | No | Use the §0.6 headings |
| C's validator | C | No | Guarded `rtm-check` step skips until it exists |

| Others need | You provide | By |
|---|---|---|
| Repo, invites, CI, `local_check.sh` | A-1 | CP1 (blocks B, C, D PRs) |
| Branch protection, labels, issues | A-3, A-5 | CP2 |
| Required `rtm-check` | A-10 | after C merges |

## 3. PR plan
| PR | Branch | Contents | Reviewer |
|---|---|---|---|
| (direct) | `main` | Bootstrap commit (A-1, A-2) | — (B verifies CI) |
| 1 | `chore/gitleaks-config` | `.gitleaks.toml` | B |
| 2 | `chore/github-templates` | PR/issue templates, CODEOWNERS | B |
| 3 | `docs/ops-docs` | `docs/ops/**` | B |
| 4 | `docs/ingest-notes-a` | 3 ingest notes | B |

## 4. Your checklist
- [ ] A-1 repo + bootstrap pushed, CI green, "repo ready" posted
- [ ] A-3 protection on and tested
- [ ] A-4 gitleaks config merged
- [ ] A-5 labels, milestones, issues created
- [ ] A-6 templates + CODEOWNERS merged
- [ ] A-7 ops docs merged
- [ ] A-8 3 ingest notes merged
- [ ] A-9 B's PRs reviewed
- [ ] A-10 `rtm-check` required and running
