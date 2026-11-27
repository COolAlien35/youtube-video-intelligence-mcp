# Requirements traceability register

Source: YouTube Video Intelligence MCP Server SRS v1.0, 9 November 2026, baseline candidate. Compare each row with its section before team approval. A row represents one requirement identifier. The SRS often specifies behavior collectively. A repeated group title preserves that ambiguity.

| Column | Interpretation |
|---|---|
| req_id, group | Unique SRS identifier and requirement family. DEC and ADR entries are design decisions. |
| title, srs_section | Individual obligation or group summary and source section in v1.0. |
| class | Mandatory (M), derived (D), or proposed (P). |
| planned_phase | Target delivery phase, 1 through 7. |
| verification | Test obligation or inclusive range from §9. A TQ row identifies its own obligation. |
| owner, issue | Responsible contributor and linked tracker issue once assigned. |
| status | Proposed → Under Review → Approved → Implemented → Verified. Approval requires team sign-off. Verification requires test evidence. |
| text_status | stated identifies individually attributed text. range-only preserves collective wording pending refinement. |
| notes | Unresolved classification, expansion phase and interpretation. |

## Review assumptions

Numeric IDs include each base number. Only the endpoint has intermediate suffixes: IF-06a, IF-09a, IF-16a/b and NFR-07a through e. FR letter ranges include each letter without a separate parent row. SEC-21 appears in the inventory but has no specific subgroup in §7. Appendix B supplies mixed classes for IF, NFR, POL and SEC; M is a provisional review choice. SK, TQ and DEV-AI default to D. §8 references the separate governance specification.

IF-01–06a is provisionally scheduled with playlist preview and approval; NFR-25–32 with provenance and constraints. The OPS split assumes the first three IDs cover configuration and health. TQ-1–13 scheduling follows the earliest relevant feature or infrastructure delivery; the group mappings are proposals. §9 groups TQ-35 with 14–18 and TQ-36 with 28–34. The assignment identifies the validator as TQ-36.

Update the CSV through a reviewed pull request. Cite the source section, requirement IDs, affected tests and issue. For baseline changes attach the §10 change request and impact assessment and update affected ADRs. Run `python scripts/validate_traceability.py --strict`. Have a human check every row against the source before advancing M/D rows to Approved.

## Phase 2 review evidence, 24 November

| Public PR | Requirements mentioned in the description | Scope of evidence |
|---|---|---|
| #3 | IF-07–16, SEC-06–09, NFR-13–24 | Shared error, identity, request and clock contracts |
| #4 | DATA-01–06, IF-16 | Canonical identifiers, durations and UTC parsing |
| #5, #7, #8 | SEC-06–09, NFR-13–24 | Logging implementation (#5) and supporting knowledge notes |
| #6 | IF-07–16, DATA-01–06, TQ-5–8 | Contributor guidance |
| #9 | IF-07–16, DATA-01–06, SEC-06–09, NFR-13–24, TQ-5–8 | Stage-review draft with outstanding integration gates |

PRs #1 and #2 update CI action versions and cite no requirement IDs. The public tracker returned nine PRs and no standalone issues. The issue column awaits real assignments. A broad PR reference supplies evidence for its component only. Advance status when the team signs off the candidate baseline and confirms implementation coverage.

### Harsh's stage-review input

- Implemented the offline provider boundary and exercised it with 140 synthetic videos, 15 channels, two isolated accounts and a channel-ineligible account. The adapter and fixture safety tests run offline.
- Learned that a missing duration and an explicit zero must survive normalization separately, and that a paged search can contain duplicate and inaccessible IDs.
- Outstanding integration checks include A's actual Settings, B's architecture error register and the issue-backed RTM update. D should spot-check IF-16 suffix expansion, missing versus zero duration, cross-account isolation and the partial-write fault case before approval.
