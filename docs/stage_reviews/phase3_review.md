# Phase 3 review · Auth and security

**28 November 2026 · Gate remains on hold.** The goal is authenticated MCP access, principal-bound encrypted Google grants, isolation testing, audited policy decisions and reachable privacy/deletion information. The integrated team gate remains open.

## Updated evidence snapshot

This update records main at 9adf71f. A's versioned AES-GCM, scoped grants and
configuration are merged. D's shared OAuth helpers (#42), compliance journal
(#43), privacy guidance (#45) and threat model (#46) are merged. Policy gates
(#44) and B's authentication/OAuth stack (#49, #51, #52, #59) are under review.

C's repaired issuer (#58), tenant suite (#70), encryption suite (#71),
transport suite (#72), injection/leakage suite (#74) and RTM update (#77)
are published. The combined branch passed 302 tests, lint, typing, RTM
validation and secret scan on Linux and Windows in
[CI run 46143621970](https://github.com/COolAlien35/youtube-video-intelligence-mcp/actions/runs/46143621970).
This run proves branch integration. Independent approval of C's PRs and
the final main build remain pending. Full playlist/MRTR execution and
approval mutation tests belong to Phase 6.

The original observations below describe the 27 November probe. Its 404s and
missing components are historical observations. Before team sign-off, replace
them with final-main results for service JWTs, OAuth, encrypted grants,
Origin/HTTPS, policy gates, reachable privacy/deletion guidance and scoped
deletion. A working deletion path and an operator contact still need evidence.

## Historical snapshot from 27 November

| Owner | Deliverable and observed status | Remaining evidence |
|---|---|---|
| A | Existing config, SQLite and green Phase 2 CI | Versioned AES-GCM keys, AAD-bound grants, scoped repository, settings/evidence declarations, HTTPS and CI evidence |
| B | Existing Origin and production guards | Verified issuer/audience, JWT middleware, fake Google callback/connect/disconnect, public privacy route |
| C | Existing provider and negative tests | FakeIssuer and Phase 3 encryption, tenant, auth and injection suites |
| D | [Errors and PKCE](https://github.com/COolAlien35/youtube-video-intelligence-mcp/pull/42), [ledger](https://github.com/COolAlien35/youtube-video-intelligence-mcp/pull/43), [gates](https://github.com/COolAlien35/youtube-video-intelligence-mcp/pull/44), [privacy](https://github.com/COolAlien35/youtube-video-intelligence-mcp/pull/45), [threat model](https://github.com/COolAlien35/youtube-video-intelligence-mcp/pull/46) | C’s human review, merge and post-merge verification |

## Gate checklist and integration observations

Local verification used main b43b779 plus D’s three code changes at a2bc482. The full local script passed 234 tests, Ruff, mypy and gitleaks. No external provider call or real credential was used.

- [x] Health returned 200 and an untrusted Origin returned 403 at /mcp.
- [x] D’s closed live gate refused provider construction with policy_gate_closed. Tests checked evidence, partial approvals and persisted gate decisions. Even a cleared test configuration has no live adapter.
- [x] The OAuth S256 reference vector, safe errors, callback-field redaction, journal append-only behavior and deletion unlinking passed on D’s branch.
- [ ] Missing-token 401 and authenticated principal/tool call. The Phase 2 MCP smoke test still succeeds without a token. Repeat with C’s fake issuer after B merges.
- [ ] Google connect, revoke/disconnect, encrypted storage, grant isolation and end-to-end secret checks. Both Google start and callback paths returned 404 during the dev probe.
- [ ] Reachable public privacy policy and working deletion path. GET /privacy returned 404. B must serve the document; disconnect and delete_data remain stubs.
- [ ] All Phase 3 deliverables reviewed, merged and green on main. The passing [main CI run](https://github.com/COolAlien35/youtube-video-intelligence-mcp/actions/runs/46043252433) predates the Phase 3 branches.

## Decisions, retrospective and carry-overs

D’s common changes come first, followed by the journal and policy PRs in dependency order. Three docs PRs can be reviewed independently. The journal migration is additive to the existing Phase 2 evidence register. Missing flags or evidence keep capabilities closed. C’s collection hook requires unit tests beneath tests/unit/, so the brief’s common and policy test files use that layout.

The reference vector and isolated HTTP probe gave reproducible results. Full integration still depends on A/B/C. [Partner feedback on C’s merged provider work](https://github.com/COolAlien35/youtube-video-intelligence-mcp/pull/34#issuecomment-7225216477) flags separate retry handling for transient reads and uncertain writes. This retrospective review is independent of human approval.

[Carry-over issue #41](https://github.com/COolAlien35/youtube-video-intelligence-mcp/issues/41) tracks the CI recovery, corrected Phase 2 record and overlapping query logs. A owns the ledger migration ordering check. Before enabling live service, owners must publish the privacy contact, demonstrate purge and confirm the retention of unlinked evidence. The original Phase 3 dates have elapsed. Human owners must decide the revised milestones or scope before committing to the 30 November release target.

Codex drafted the implementation, documents and tests and checked observable outcomes against the brief. Source checks prevented a fabricated Google-flow success or privacy-route claim. Run the complete fake flow again after all owner PRs merge and record the main SHA, CI run, reviewer sign-offs and results here before opening Phase 4.
