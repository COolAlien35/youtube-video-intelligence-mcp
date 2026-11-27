# Project query log

## Phase 1 queries

Person D · 2026-11-22 · Queries against five available source notes

### Can an approved playlist proposal unlock a live demo?

No. Approval authorizes the specific user action. The project separately requires platform clearance for the interface and affected features. Use fixtures while clearance is pending. [[live-access-decisions]]

### Does a green rtm-check prove the RTM validates?

Only when the job executed the validator on the actual matrix. Inspect the log and record the checked revision. At bootstrap the job may skip validation. [[release-evidence]]

### Would two concurrent requests get independent writable SQLite ledgers?

The design puts a shared ledger on the single instance’s persistent disk. WAL permits concurrent readers but serializes writers. Test reservation contention and verify both requests against the shared budget. The vault has design evidence only. [[persistent-state]]

## Phase 2 queries

### Which value should middleware restore after a nested request scope?

Save the token from request_id_var.set(rid) on entry and reset it in a finally block on exit. This recovers the caller’s previous value even when an exception interrupts handling. The context variable belongs to the active async context. [Source note](../../../second-brain/3-resources/ingest/ingest_D_structured-logging.md)

### Where should a redaction test inspect a substituted message?

Read the JSON line emitted by the configured handler. A secret may enter through formatting arguments, exception text or nested extra attributes. Exercise each path and check the serialized line for the synthetic secret. Then assert that the expected request ID remains present. [Distilled note](../../../second-brain/2-areas/request-logging.md)
