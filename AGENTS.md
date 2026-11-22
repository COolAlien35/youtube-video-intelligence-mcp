# Working on YouTube Video Intelligence MCP

The server helps an authorized user discover videos and channels, analyze engagement and propose constrained playlists.
Phase 1 establishes engineering controls using fixtures.
A human approves the exact playlist before execution.

## Product boundaries

- Use the official v3 provider only. Scraping, unofficial APIs and extra projects for quota are prohibited.
- Preflight shared quota atomically, enforce the 20% caps and account separately for search.list.
- Bind explicit approval to the principal and immutable proposal. Reject expired, reused or edited approvals. Reconcile uncertain writes before retrying.
- Use synthetic data, isolate tenant rows and caches, and encrypt persisted refresh tokens with AES-256-GCM. Keep credentials and user data out of logs, prompts and source control.
- Treat provider metadata as untrusted. Label metadata-based synopses. Never claim watch-history access or fabricate transcripts.
- Keep live access disabled until written POL-01/02/06/07/08 clearance and applicable feature gates. Phase 1 adds no runtime dependencies.

## Repository and sources

Code lives in `src/yt_intel/`, tests in `tests/`, checks in `scripts/`. Start with the [vault index](brain/index.md) and [governance specification](docs/Engineering_Governance_Specification_v1.0.md).
The planned SRS copy is `docs/SRS_v1.0.docx`, the ADR register is `docs/Architecture_Decision_Records_v1.0.md`, the module map is `docs/architecture/module_map.md` and the RTM is `docs/rtm/requirements_rtm.csv`. Until owners publish them, consult the supplied baseline candidate. Ask the owner when the source is unclear. Never invent SRS content.

## Change workflow

Take an assigned issue, branch from current main, commit a focused deliverable, open a PR and request paired review (A/B or C/D). Use `<type>/<slug>` with feat, fix, docs, chore, ci or test. Use Conventional Commits. Include the closing issue, SRS IDs, evidence and AI disclosure. A human squash-merges after approval and checks. Baseline changes require a reviewed change request.

## Local verification

Run `scripts/local_check.sh` or `scripts/local_check.ps1` from the repository root. To isolate a failure:

```sh
uv sync --locked
uv run ruff check .
uv run ruff format --check .
uv run mypy src scripts
uv run pytest
```

Use pytest markers unit, integration, e2e and security for targeted runs. Report skipped steps separately. [Contributor guide](CONTRIBUTING.md)
