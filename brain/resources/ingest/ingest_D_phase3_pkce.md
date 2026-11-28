# PKCE verification evidence

## Source

[RFC 7636 §§4.1–4.6 and Appendix B](https://www.rfc-editor.org/rfc/rfc7636.txt).

## Ingested by / date

Person D · 2026-11-27 · AI-assisted draft

## Summary

Create a fresh verifier for an authorization attempt.
Hash its ASCII bytes with SHA-256.
Encode the digest with the URL-safe Base64 alphabet and omit padding.
The challenge goes to authorization and the verifier goes to code exchange.
OAuth state is an independently generated value checked on the callback.

## Key facts

- RFC 7636 §4 specifies the S256 transformation and verifier character constraints.
- Appendix B supplies a deterministic verifier/challenge pair for regression testing.

## Relevance

IF-17–23, SEC-01–09. D tests the transformation, B must bind and expire attempts.

## Open questions / risks

Full flow verification awaits the fake authorization server and callback routes.

## Links

[[project-index]] · [Shared helper PR](https://github.com/COolAlien35/youtube-video-intelligence-mcp/pull/42)
