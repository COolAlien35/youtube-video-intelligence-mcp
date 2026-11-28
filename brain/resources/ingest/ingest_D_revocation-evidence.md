# Revocation and compliance journal privacy

## Source

[YouTube Developer Policies, authorization and revocation](https://developers.google.com/youtube/terms/developer-policies), project SRS §§2.3, 5.2 and 7.

## Ingested by / date

Person D · 2026-11-27 · AI-assisted draft

## Summary

Revocation stops continued use of an account grant.
Start the project’s seven-calendar-day purge deadline when revocation or deletion is requested.
Record a minimal event instead of copying account content or callback parameters.
Keep the principal lookup separate so a purge can unlink the journal.
Use the earlier applicable deadline when normal retention and deletion overlap.

## Key facts

- Developer Policies III.E.2 covers revocation and deletion of authorized data.
- SRS §5.2 supplies the five-minute, 24-hour, seven-day and 30-day project windows.

## Relevance

POL-04/05, DATA-22–26. Verify both tenant-safe purge and preserved non-identifying event history.

## Open questions / risks

Unlinked operational evidence needs an approved retention period before live release.

## Links

[[live-access-decisions]] · [Compliance ledger](https://github.com/COolAlien35/youtube-video-intelligence-mcp/pull/43)
