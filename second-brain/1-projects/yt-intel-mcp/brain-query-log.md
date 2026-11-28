# Phase 2 query log

## Which value should middleware restore after a nested request scope?

Save the token from request_id_var.set(rid) on entry and reset it in a finally block on exit. This recovers the caller’s previous value even when an exception interrupts handling. The context variable belongs to the active async context. [Source note](../../3-resources/ingest/ingest_D_structured-logging.md)

## Where should a redaction test inspect a substituted message?

Read the JSON line emitted by the configured handler. A secret may enter through formatting arguments, exception text or nested extra attributes. Exercise each path and check the serialized line for the synthetic secret. Then assert that the expected request ID remains present. [[request-logging]] · [Distilled note](../../2-areas/request-logging.md)
