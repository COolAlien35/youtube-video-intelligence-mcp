# YouTube Video Intelligence MCP

A Model Context Protocol (MCP) server that analyses YouTube video content — extracting metadata, transcripts, and intelligent summaries — and exposes them as structured tool outputs for LLM-powered applications.

> **Status:** Phase 1 — Foundation & Governance.
> Live YouTube API access is disabled until POL-01–08 gates clear.

## Quickstart

### Prerequisites

- **Python 3.12** (installed automatically by uv from `.python-version`)
- **[uv](https://docs.astral.sh/uv/) 0.11.32** — the pinned version for this project

Install uv 0.11.32:

```bash
# macOS / Linux / Git Bash
curl -LsSf https://astral.sh/uv/0.11.32/install.sh | sh

# Windows PowerShell
powershell -ExecutionPolicy Bypass -c "irm https://astral.sh/uv/0.11.32/install.ps1 | iex"
```

### Setup

```bash
git clone https://github.com/COolAlien35/youtube-video-intelligence-mcp.git
cd youtube-video-intelligence-mcp
uv sync --locked
```

### Run checks

```bash
# macOS / Linux / Git Bash
scripts/local_check.sh

# Windows PowerShell
powershell -ExecutionPolicy Bypass -File scripts\local_check.ps1
```

The script runs, in order: **lint** (ruff) → **format check** (ruff) → **type check** (mypy) → **tests** (pytest).

## Documentation

- [`docs/ops/dev_environment.md`](docs/ops/dev_environment.md) — full setup guide (macOS, Linux, Windows)
- [`docs/ops/ci_overview.md`](docs/ops/ci_overview.md) — CI jobs, required checks, and policies
- [`docs/ops/infra_prerequisites.md`](docs/ops/infra_prerequisites.md) — infrastructure checklist (Phase 2+)
- [`docs/tools/playlist_workflow.md`](docs/tools/playlist_workflow.md) — FR-5 playlist creation, approval flow, and `video-to-playlist` skill
- [`docs/policy/write_gating.md`](docs/policy/write_gating.md) — `POL-04/05/07/08` and `PLAYLIST_WRITES_ENABLED` write gating
- [`docs/skill_eval.md`](docs/skill_eval.md) — manual skill evaluation protocol and scenario matrix

## Playlist Skill (`video-to-playlist`)

The packaged skill at [`skills/video-to-playlist/SKILL.md`](skills/video-to-playlist/SKILL.md) guides an MCP client through `similar_videos` → `propose_playlist` (immutable preview, zero writes) → explicit user confirmation → `confirm_execute_playlist` → `operation_status`. Live playlist writes remain disabled (`PLAYLIST_WRITES_ENABLED=false`) until policy gates clear. Validate the skill and evaluation traces with:

```bash
uv run python scripts/validate_skill.py
uv run python scripts/check_skill_traces.py skills/video-to-playlist/evals/traces/good_happy.json
```

## Project structure

```
src/yt_intel/          # Main package (src layout)
tests/                 # Test suite
scripts/               # Helper scripts (local checks, validators)
docs/                  # Documentation, ADRs, ops guides
second-brain/          # Knowledge base (ingest notes, refined notes)
.github/               # Workflows, templates, CODEOWNERS
```

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md) (coming in Phase 1).

## License

License: TBD (see [decision D3](docs/plan.md#3-decisions)).
