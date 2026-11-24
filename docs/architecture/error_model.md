# Application error contract

SRS §§3.2, 6–7 specify handling. The uppercase wire names align with the Phase 2 common-core proposal. Transport-level Origin rejection uses HTTP 403. Tool failures carry a public error inside the structured tool result.

```json
{"code":"RATE_LIMITED","message":"Try again after the indicated delay.","details":null,"retryable":true,"retry_after":30,"request_id":"example-request"}
```

Return exactly code, message, details, retryable, retry_after and request_id. Use null for unavailable details, retry delay or correlation. Retry delay is expressed in seconds when known. Details must be JSON-serializable and safe for this principal. Exclude tokens, raw upstream errors, stack traces and chains. Retryable describes the current operation; user remediation or a later fresh request is a separate action.

| Code | Retryable? | Raised by | Server handling | Client guidance |
|---|---|---|---|---|
| INVALID_INPUT | No | Validation | Reject malformed IDs and inputs before provider access | Correct the specified field |
| NOT_FOUND_OR_UNAVAILABLE | No | Provider | Preserve unavailable/private/deleted status without fabricating metadata | Remove the item or select another |
| AUTH_REQUIRED | No | Auth | Stop account-scoped calls | Connect and authorize the correct account |
| AUTH_EXPIRED_OR_REVOKED | No | Auth/provider | Stop using the invalid grant | Reauthorize before a fresh request |
| CHANNEL_REQUIRED | No | Provider/eligibility | Map youtubeSignupRequired and abort before writing | Use an eligible account with a channel |
| QUOTA_EXCEEDED | Conditional after replenishment | Quota/provider | Reject over-budget preflight with no upstream call; stop on upstream exhaustion | Reduce scope or wait for budget reset |
| RATE_LIMITED | Conditional after delay | Fairness/provider | Return known delay, bound retries on transient reads | Wait before starting again |
| NO_COMPLIANT_PLAYLIST | No | Feature/constraint validation | Explain the shortfall and preserve hard constraints | Explicitly change constraints for a new proposal |
| STALE_APPROVAL | No | Approval | Reject used, changed or expired approval before writing | Preview again and approve the new snapshot |
| WRITE_UNCERTAIN | No automatic replay | Execution/provider | Save operation and item status; reconcile remote state first | Poll the operation and follow reconciliation guidance |
| FORBIDDEN | No | Auth/storage | Deny tenant mismatch without leaking another tenant’s objects | Use the authorized principal |
| POLICY_GATE_CLOSED | No | Policy | Stop affected action before protected work | Use the fixture workflow or await clearance |
| UPSTREAM_ERROR | Transient reads only | Provider | Bound backoff by deadline; route uncertain writes to reconciliation | Follow retry guidance for reads |
| NOT_IMPLEMENTED | No | Stub tool | Return a structured unavailable-feature result | Wait for implementation |
| INTERNAL_ERROR | No by default | Server boundary | Return generic public message and correlate private diagnostics | Report the request ID |

For partial success, report the known playlist ID, per-item outcomes and operation reference to the authorized caller. A known partial outcome uses operation state; a lost write response uses WRITE_UNCERTAIN. Never treat either as permission to repeat all inserts.

## Phase 2 changes · 25 November 2026

The server HTTP adapter maps each of the 15 common ErrorCode values in one table. A disallowed Origin returns HTTP 403 with FORBIDDEN and the diagnostic request ID. Unexpected application exceptions receive a generic INTERNAL_ERROR response. Tool stubs return NOT_IMPLEMENTED inside the structured result delivered by MCP; its HTTP transport can succeed while the application envelope has ok=false. The registry and HTTP tests check the distinction. The existing code catalogue already contains NOT_IMPLEMENTED. [Server adapter](https://github.com/COolAlien35/youtube-video-intelligence-mcp/pull/14) · [Tool implementation](https://github.com/COolAlien35/youtube-video-intelligence-mcp/pull/15)
