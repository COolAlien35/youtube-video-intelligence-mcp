# Google delegated access and grant expiry

## Source

[Google web-server authorization](https://developers.google.com/identity/protocols/oauth2/web-server), [token expiration](https://developers.google.com/identity/protocols/oauth2#expiration) and [RFC 7636 PKCE](https://www.rfc-editor.org/rfc/rfc7636).

## Ingested by / date

Person B deliverable · 2026-11-25 · AI-assisted draft for review

## Summary

A signed-in MCP user can separately authorize Google account access.
The project requests read scopes first and asks for additional permission when playlist creation is enabled.
Bind the callback to the original authorization attempt using state, the registered redirect URI and PKCE.
Persist refresh tokens encrypted with the recorded key version.
A revoked or expired grant stops the account operation until the user authorizes it again.

## Key facts

Google documents incremental authorization and offline access in the web-server guide. For an external consent screen in Testing, refresh tokens expire after seven days unless only the listed basic identity scopes are requested (Google token expiration). PKCE binds code redemption to a verifier (RFC 7636); this project requires it in SRS §7.

## Relevance

IF-17–23, SEC-06–09, TQ-9–13. Test expired grants, withheld write scope and an account without a channel using synthetic responses.

## Open questions / risks

Confirm the consent-screen publishing status and granted scopes in the target project. A valid OAuth grant does not clear POL-08.

## Links

[[ingest_B_mcp-confirmation]]
