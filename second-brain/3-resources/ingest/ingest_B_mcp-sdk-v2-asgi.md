# Mounting the MCP Python SDK in an ASGI service

## Source

[MCP Python SDK 2.3.0 release](https://pypi.org/project/mcp/2.3.0/), [SDK ASGI integration](https://py.sdk.modelcontextprotocol.io/run/asgi/), [SDK MRTR guide](https://py.sdk.modelcontextprotocol.io/handlers/multi-round-trip/), [July 2026 HTTP transport](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http).

## Ingested by / date

Person B deliverable · 2026-11-25 · AI-assisted, exercised locally on Python 3.12

## Summary

The host app owns the health route and starts the mounted transport’s lifespan.
The SDK owns the /mcp route and derives discovery schemas from typed callables.
Its July protocol exchanges messages per request and carries confirmation input across rounds.
The project can therefore keep a stateless transport while storing deliberate approval state later.
An HTTP-level client test observes both the result envelope and the request ID added by the host.

## Key facts

- Entering the child app’s lifespan initializes the transport manager for requests. Mounting paths must compose to /mcp exactly. [ASGI guide](https://py.sdk.modelcontextprotocol.io/run/asgi/)
- A supplied invalid Origin receives 403. A missing Origin does not itself require rejection. The July revision removes protocol-level sessions. [Transport specification](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http)
- MCPServer.add_tool produced the nine typed input/output schemas; the server-injected principal was absent from discovery. The in-process client verified structuredContent and header correlation for both protocol flows. [Test evidence](https://github.com/COolAlien35/youtube-video-intelligence-mcp/pull/15)
- InputRequiredResult provides the continuation mechanism. The application's five-minute, single-use approval must still bind to the principal and immutable proposal. [SDK MRTR guide](https://py.sdk.modelcontextprotocol.io/handlers/multi-round-trip/)

## Relevance

IF-07–11, IF-09a, SEC-20, NFR-13–24 and TQ-3/5. Repeat the HTTP smoke test after introducing real settings, auth or features.

## Open questions / risks

A must supply the dependency lock and validated settings. Phase 6 still needs a Claude Desktop interoperability demonstration; SDK support alone cannot establish that result.

## Links

[[ingest_B_mcp-confirmation]] · [Phase 1 source note](https://github.com/COolAlien35/youtube-video-intelligence-mcp/blob/05b777f/second-brain/3-resources/ingest/ingest_B_mcp-confirmation.md) · [SDK verification](https://github.com/COolAlien35/youtube-video-intelligence-mcp/pull/13)
