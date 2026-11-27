# Verifying request correlation and redaction

An application log entry is complete only after message substitution, context lookup and extra-field processing. Test the serialized event from the application handler. Assert that it parses as one JSON object, keeps the correct request ID and contains none of the synthetic credential values. Include two overlapping tasks to detect accidental use of global request state. During server integration, check a named application logger and each separately configured handler.

The current Phase 2 source is [[ingest_D_structured-logging]]. The published tests distinguish unit-level guarantees from server wiring. [Research note](../3-resources/ingest/ingest_D_structured-logging.md) · [Logging PR](https://github.com/COolAlien35/youtube-video-intelligence-mcp/pull/5)

**Coverage of the phase.** A, B and C’s Phase 2 notes were unavailable at compilation. Revisit the quota, SDK and fixture findings when their source notes land. The earlier A notes document Phase 1 research and do not establish Phase 2 integration outcomes.
