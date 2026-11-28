# Harsh contribution and Phase 3 integration audit

Snapshot from 28 November 2026, main c874300.

## Attribution

Git identifies Harsh's commits as Harsh Kumar with the configured address
harsh.kumar21680@gmail.com. The GitHub API links the child squash commits
to harsh-kumar-005. The identity is already recognized.

Main has eight commits with an explicit Co-authored-by trailer for Harsh:
#34, #43, #44, #47, #49, #51, #52 and #59. PR #34 contains C's Phase 1/2
stack, authored primarily by Pulkit Pandey. The other listed commits preserve
credit for Harsh's integration changes. The screenshot's empty primary-author
listing does not remove the recorded co-author credits.

## Phase 3 merge destinations

| PR | State | Merge destination |
|---|---|---|
| #77 | Merged | test/p3-c-injection-and-leak |
| #74 | Merged | test/p3-c-origin-auth-https |
| #72 | Merged | test/p3-c-tenant-isolation |
| #71 | Merged | test/p3-c-tenant-isolation |
| #70 | Merged | test/p3-c-fake-issuer-fixtures |
| #58 | Open | main |

All child changes are present in the #58 tree. Main still lacks the C issuer
and security suite until #58 merges. A squash merge of that root will create
one aggregate main commit; the original development commits remain available
on the feature branches. Check the final commit's author and co-author
trailers when merging contributions.

## Work through Phase 3

- Phase 1/2 C artifacts are on main through #34. The baseline matrix still
  requires row-by-row human review and team approval. Existing range-only
  entries, owner/issue assignments and lifecycle states require team disposition.
- Phase 3 issuer, tenant isolation, encryption, Origin/auth/HTTPS, injection
  boundary, secret leakage, policy denial and RTM evidence are implemented in #58.
- D's fingerprint feedback is addressed using public key material, with a
  regression test for public-JWKS reproducibility and rotation.
- Public privacy and deletion guidance now have an unauthenticated route test.
- The full branch passes 324 tests and the standard lint/format/type/RTM checks.
- Paired human approval, root merge, final main CI and the joint stage-review
  sign-off remain pending. Full playlist execution/MRTR acceptance belongs to Phase 6.

## Outstanding reviews assigned to Harsh

The previous Phase 3 review queue (#42–47, #49, #51, #52, #59 and #60)
is merged. The current requested reviews are:

| Phase | PR sequence |
|---|---|
| 4 | #62, #63, #64, #65, #66 |
| 5 | #69, #73, #78, #80 |
| 6 | #91, #92, #93, #94 |

These are pending review. Earlier review findings for the Phase 4 chain
must be rechecked against its current heads before approval.

The Phase 4/5 C assignment files have been read for dependency planning.
Their implementation begins after the earlier gate is accepted. Phase 4
adds the shared ranking engine, provider call evidence, fixtures and benchmark.
Phase 5 adds account fixtures and real-MCP acceptance/isolation/logging suites.
