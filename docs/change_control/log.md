# Change Control Log

All baseline interpretations and SRS extensions follow the status path `Proposed` → `Under Review` → `Approved` → `Implemented` → `Verified` (using [TEMPLATE.md](TEMPLATE.md)). Person B reviews ADR impact for each entry.

| ID | Title | Status | Affected IDs | Owner | Summary & Impact |
|---|---|---|---|---|---|
| `CR-01` | Principal-scoped cache scope & TTL ceiling | `Implemented` | `DATA-24`, `NFR-08` | A / D | Cache keys are strictly scoped by `(principal, kind, key)` with per-feature TTL (e.g., 24 h) and a hard 30-day ceiling from `fetched_at`. |
| `CR-02` | Channel similarity weights (`FR-2`) | `Under Review` | `FR-2` | D / C | Deterministic text-similarity weights over fixture-available channel metadata fields; no cross-owner aggregation without `POL-06`. |
| `CR-03` | Engagement duration band edges (`FR-4`) | `Under Review` | `FR-4` | D | Duration bands: `under_10m` (`<600s`), `10_to_under_30m` (`600–1799s`), `30_to_60m` (`1800–3600s`), `over_60m` (`>3600s`), `unknown` (non-int/negative). |
| `CR-04` | Category name handling (`FR-4`) | `Under Review` | `FR-4` | D | Display category names only when already present on fetched video metadata; never charge extra `videoCategories.list` quota calls. |
| `CR-05` | Discovery pool size (`POOL=50`) vs 20-call `search.list` cap | `Under Review` | `FR-1`, `QUOTA-01` | B / A | Bound `similar_videos` candidate pool to 50 items (1 `search.list` page + batched `videos.list`) to preserve the 20-call/day shared search cap. |
| `CR-06` | Missing-tags weight redistribution (`FR-1`) | `Under Review` | `FR-1` | B / C | When `tags` are absent (`None` vs `[]`), redistribute tag weight deterministically across title/description/category signals rather than failing. |
| `CR-07` | Terminal fate of `PARTIALLY_COMPLETED` operations | `Proposed` | `FR-5`, `DATA-23` | A / D | Keep `PARTIALLY_COMPLETED` operations resumable until the 24-hour retention sweep, which marks them `FAILED` with a partial flag before purge. |
| `CR-08` | Write reconciliation fingerprint | `Proposed` | `FR-5`, `IF-21` | A / B | Embed a short proposal reference token in the previewed description (fallback: exact title, privacy, and creation window); stop on `>1` match (`ReconciliationAmbiguousError`). |
| `CR-09` | Default playlist item limit (`10`, hard max `20`) | `Implemented` | `FR-5`, `QUOTA-02` | A / D | `YT_INTEL_MAX_PLAYLIST_ITEMS=10` (hard max `20`) bounds single-playlist write cost to `550` units (`50 + 50N`) within the `2000`-unit common daily cap. |
| `CR-10` | Compliance ledger principal hashing on deletion | `Proposed` | `DATA-25`, `POL-05` | A / D | Retain minimal audit events after `delete_data` / `forget_principal` while erasing the principal lookup association / replacing with a salted hash. |
| `CR-11` | Quota ledger counter pruning at 30 days | `Proposed` | `DATA-24`, `QUOTA-01` | A | Prune daily quota counter rows older than 30 days during the retention sweep while preserving current Pacific-day accounting. |
| `CR-12` | MRTR confirmation & two-step handle fallback | `Under Review` | `FR-5`, `IF-19` | B / D | Prefer MCP SDK input-required MRTR; if client/SDK lacks interactive elicitation, require explicit `confirm_execute_playlist` with the 5-minute single-use handle. |
