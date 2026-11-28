# YouTube Video Intelligence MCP

A Model Context Protocol (MCP) server that discovers related YouTube videos and channels, summarizes authorized account engagement, and creates constrained, user-approved playlists using official YouTube Data API v3 semantics and deterministic offline fixtures.

> **Live YouTube access is disabled** (`YT_INTEL_LIVE_YOUTUBE_ENABLED=false`, `YT_INTEL_PLAYLIST_WRITES_ENABLED=false`) until written `POL-01`–`POL-08` determinations arrive. See [`docs/policy/gate_status.md`](docs/policy/gate_status.md) and [`docs/policy/evidence_requests.md`](docs/policy/evidence_requests.md).

## What It Is (and Is Not)

- **Is:** A multi-tenant, authenticated MCP server (`mcp==2.3.0`, FastAPI, SQLite/WAL) with principal-scoped storage and caching, atomic Pacific-day quota preflight, encrypted delegated Google OAuth grants, and human-in-the-loop playlist creation.
- **Is not:** A scraper, an unauthenticated proxy, a transcript fabricator, or a watch-history reader (YouTube Data API v3 does not expose watch history). Metadata similarity measures text/tag overlap, not factual quality or accuracy.

## MCP Tool Catalog

| Tool | Purpose | Auth / Scope | Writes |
|---|---|---|---|
| `similar_videos` | Seed resolution (`seed.metadata`, untrusted) & bounded ranked video discovery | MCP Bearer | None |
| `similar_channels` | Exact channel ref parsing & ranked similar channels | MCP Bearer | None |
| `recommendations` | Personalized video recommendations from linked account signals | MCP Bearer + Google Read | None |
| `engagement_analysis` | Descriptive UTC-window metrics & duration bands over account signals | MCP Bearer + Google Read | None |
| `propose_playlist` | Constraint-filtered preview (`50 + 50N` quota estimate) + SHA-256 digest | MCP Bearer + Google Read | Local proposal only |
| `confirm_execute_playlist` | Single-use 5-min MRTR approval bound to principal, channel & digest | MCP Bearer + Google Write | Approved playlist & items |
| `operation_status` | Principal-scoped execution progress & per-item reconciliation status | MCP Bearer | None |
| `disconnect_google` (`disconnect`) | Revoke Google grant, delete local grant, purge account cache | MCP Bearer | Revokes/unlinks grant |
| `delete_data` | Principal-scoped local data deletion request & 7-day purge receipt | MCP Bearer | Deletes local account data |

## Security, Approval & Limitations

- **Zero writes before approval:** `propose_playlist` produces an immutable snapshot (`5`-minute expiry). Editing title, description, visibility (`private` default), channel, or video order supersedes the proposal and invalidates prior approvals.
- **Write-before-call journaling:** Every `playlists.insert` / `playlistItems.insert` is journaled (`INSERTING`) before the upstream call and reconciled before any resume.
- **Quota & API limits:** Shared daily cap of `2,000` common units (`50 + 50N` per playlist) and `20` `search.list` calls/day; account signal caps include `1,000` liked videos, `500` subscriptions, and `200` playlists.
- **Retention windows:** `5` min (unexecuted proposals/handles/OAuth state), `24` h (terminal proposals & operations), `7` days (deletion & revocation backstop), `30` days (API cache ceiling from `fetched_at`).

## Quickstart & Checks

Prerequisites: Python `3.12` and pinned [`uv` `0.11.32`](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/COolAlien35/youtube-video-intelligence-mcp.git
cd youtube-video-intelligence-mcp
uv sync --locked

# Full check suite: ruff lint + format, mypy, pytest
scripts/local_check.sh
# Windows PowerShell:
# powershell -ExecutionPolicy Bypass -File scripts\local_check.ps1

# Skill, trace, docs, and policy checks
uv run python scripts/validate_skill.py
uv run python scripts/check_skill_traces.py skills/video-to-playlist/evals/traces/good_happy.json
uv run python scripts/check_docs.py
uv run python scripts/policy_status.py
```

## Playlist Skill (`video-to-playlist`)

Install or load [`skills/video-to-playlist/SKILL.md`](skills/video-to-playlist/SKILL.md) into your MCP client. It enforces the six-step workflow (`similar_videos` → metadata synopsis → `propose_playlist` preview → explicit user confirmation → `confirm_execute_playlist` → `operation_status`) and stops without writes on any failure, denial, or untrusted metadata injection attempt.

## Documentation & Contributing

- [`docs/index.md`](docs/index.md) — full documentation index
- [`docs/ops/render_secrets_and_https.md`](docs/ops/render_secrets_and_https.md) & [`docs/ops/infra_prerequisites.md`](docs/ops/infra_prerequisites.md) — deployment & ops guides
- [`CONTRIBUTING.md`](CONTRIBUTING.md) & [`AGENTS.md`](AGENTS.md) — workflow, paired reviews (`A↔B`, `C↔D`), and conventions
- [`RELEASE_NOTES.md`](RELEASE_NOTES.md) — release candidate notes
