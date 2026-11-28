# Supabase identity and principal scope

## Source

[Supabase OAuth 2.1 server](https://supabase.com/docs/guides/auth/oauth-server), [discovery and setup](https://supabase.com/docs/guides/auth/oauth-server/getting-started) and [OpenID Connect subject identifiers](https://openid.net/specs/openid-connect-core-1_0.html#SubjectIDTypes).

## Ingested by / date

Person B deliverable · 2026-11-25 · AI-assisted draft for review

## Summary

Supabase can act as the authorization server for the MCP service.
Discovery exposes provider metadata and where to find its signing keys.
The service validates the access token for its intended use before accepting identity claims.
The project uses issuer and subject together as the durable principal identifier.
A Google grant for that principal is a separate authorization record.

## Key facts

The Supabase server supports OAuth authorization code flow with PKCE and OIDC discovery (Supabase OAuth server guide). OIDC subjects are local to an issuer (OIDC Core §8). SRS §§3.2 and 7 bind each Google grant to a verified MCP principal.

## Relevance

IF-17–23, SEC-01–05 and SEC-10–19. Exercise a two-principal lookup with the same object identifier.

## Open questions / risks

Confirm the target project’s issuer and accepted audience during deployment. Avoid storing any live configuration values in the vault.

## Links

[[ingest_B_google-grants]]
