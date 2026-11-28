# Streamable HTTP and playlist confirmation

## Source

[MCP 2026-07-28 Streamable HTTP](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http), [protocol release](https://blog.modelcontextprotocol.io/posts/2026-07-28/) and [Python SDK MRTR](https://py.sdk.modelcontextprotocol.io/handlers/multi-round-trip/).

## Ingested by / date

Person B deliverable · 2026-11-25 · AI-assisted draft for review

## Summary

The remote service accepts MCP requests on an HTTP endpoint.
Validate the Origin at ingress before dispatching a tool.
When an action requires a choice, the first call can return an input request.
The client collects the response and submits the original call again with the continuation data.
The application verifies that this principal approved this exact playlist before consuming its handle.

## Key facts

An HTTP response can deliver JSON or a request-scoped SSE stream (transport spec). An invalid supplied Origin is rejected with HTTP 403 (transport security section). The client resubmits inputResponses with echoed requestState when supplied (protocol release and SDK). The five-minute single-use rule comes from project SRS §3.1.

## Relevance

IF-01–11, SEC-20, FR-5. Use a fixture to show zero writes on decline, expiry or edited proposal.

## Open questions / risks

Verify the target Claude Desktop build handles the confirmation flow end to end. Protocol support alone cannot demonstrate client behavior.

## Links

[[ingest_B_service-principal]]
