# Playlist workflow & `video-to-playlist` skill (FR-5)

The `FR-5` playlist creation workflow turns a seed video into a constraint-filtered, user-approved YouTube playlist without ever writing before explicit confirmation.

## Tools in the workflow

| Tool | Purpose | Writes |
|---|---|---|
| `similar_videos` | Resolves the seed video, exposes untrusted `seed.metadata` (for a clearly labelled metadata-based synopsis), and returns ranked candidate videos. | None |
| `propose_playlist` | Filters candidates against deterministic constraints (total duration cap, per-video max, spoken language, excluding unknown durations/languages under strict filters), computes `50 + 50N` quota units, and returns an immutable preview + SHA-256 snapshot digest. | None (local proposal only) |
| `confirm_execute_playlist` | Accepts the 5-minute single-use MRTR approval handle bound to the verified principal, Google account, eligible channel, and snapshot digest; journals each item before calling `playlists.insert` / `playlistItems.insert` and reconciles uncertain writes before any resume. | Approved playlist & item writes |
| `operation_status` | Returns principal-scoped execution progress, per-item outcomes (`PENDING`, `INSERTING`, `INSERTED`, `FAILED`, `UNCERTAIN`), and reconciliation status. | None |

## Approval & safety flow

1. **Zero writes before approval:** `propose_playlist` only creates a local `PROPOSED` snapshot (5-minute expiry).
2. **Edit invalidation:** Changing title, description, visibility (`private` by default), target channel, or video order supersedes the prior proposal and invalidates any previous approval handle.
3. **Channel & scope checks:** Missing channels or `youtubeSignupRequired` return `ChannelRequiredError`; missing write scope returns `WriteScopeRequiredError` for incremental consent.
4. **Untrusted metadata boundary:** Video titles, descriptions, and tags are sanitized via `sanitize_untrusted()` and treated strictly as data, never as instructions or approval handles.
5. **Policy gate & runtime switch:** Live writes stay disabled unless `POL-04`, `POL-05`, `POL-07`, `POL-08`, and `PLAYLIST_WRITES_ENABLED=true` are all active (see [Write gating](../policy/write_gating.md)).

## Using the `video-to-playlist` skill

The packaged skill lives at [`skills/video-to-playlist/SKILL.md`](../../skills/video-to-playlist/SKILL.md) and enforces the six-step workflow (`resolve seed` → `metadata synopsis` → `similar_videos` → `propose_playlist` + full preview → `confirm_execute_playlist` after explicit confirmation → status report).

Validate the skill structure and evaluation traces locally:

```bash
uv run python scripts/validate_skill.py
uv run python scripts/check_skill_traces.py skills/video-to-playlist/evals/traces/good_happy.json
```

See [`docs/skill_eval.md`](../skill_eval.md) for the manual Claude Desktop evaluation protocol across all eight scenarios.
