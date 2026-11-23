# Testing the YouTube intelligence server

Most tests exercise deterministic Python functions. Integration tests join the fixture provider, SQLite, quota ledger and fake clock. A small MCP end-to-end suite drives the actual tool interface, checking both the response envelope and persisted side effects. Each level runs offline.

| SRS §9 obligations | First phase | Test location and evidence |
|---|---:|---|
| TQ-1–4 | 4 | unit/ranking checks scores and ties; integration/provider checks normalized data; e2e checks tools and invalid inputs. Extend with each feature. |
| TQ-5–6 | 2 | unit/provider scans fixtures; integration/quota rejects over-budget concurrent reservations. |
| TQ-7–8 | 6 | e2e covers skill success, denial and regression cases. |
| TQ-9 | 3 | integration/auth checks encrypted storage and incremental scopes. |
| TQ-10–13 | 6 | e2e checks approval, injection, channel errors, reconciliation and provenance. |
| TQ-14–18, 35 | 1 | CI, reviewed PR and protection evidence; root smoke and validator tests run in pytest. |
| TQ-19–27 | 7 | integration tests exercise retention with a fake clock, both quota buckets and OAuth; e2e exercises language, like limits and attribution. |
| TQ-28–34 | 7 | integration tests exercise two principals, Origin and shared quota; unit/ranking evaluates relevance. Inspect CI permissions in workflow review. |
| TQ-36 | 1 | tests/test_validate_traceability.py validates temporary cases and the real matrix. |

Paths in the table are relative to tests/. Group obligations follow the SRS. Proposed coverage targets for discussion are 85% line coverage overall and branch coverage of every error and pre-write decision. A feature is ready for review when its positive, boundary and failure cases pass, tests carry the unit, integration or e2e marker plus security where applicable, and its RTM row links the issue and verification evidence.

## Demonstrations

| Demo | Synthetic setup | Observable end-to-end assertion |
|---|---|---|
| A | Two-hour playlist cap, maximum 20 minutes per video, strict language, missing fields | Every selected item meets all constraints; no writes before approval. |
| B | Approve a snapshot then change title, visibility, channel or ordering | Each mutation invalidates approval; insertion count stays zero. |
| C | user_nochannel | Recoverable channel-required response with no playlist creation. |
| D | Remaining budget below workflow cost | No provider call, no budget debit, rejection recorded. |
| E | Timeout on a numbered item insertion | Inspect operation status and reconcile existing items before retry; no duplicate insertion. |
| F | Instructions embedded in metadata | Returned metadata stays data; a write still requires a valid approval. |
| G | Two principals with distinct accounts and overlapping request times | Each sees only its records; cross-user approval and deletion fail. |

## Phase 7 ranking evaluation

Freeze a synthetic query set, candidate catalogue and relevance judgments before tuning. Record graded relevance (0–3) per query and video, corpus version, K and canonical-ID tie-break. Calculate Precision@K with relevance above zero and denominator K. For NDCG@K use gain 2^grade − 1 and log2(rank + 1) discount; divide by ideal DCG for the same pool. Report queries with zero ideal gain separately. Publish per-query scores, macro averages and comparison against a fixed baseline. Keep tuning queries separate from the reported set.
