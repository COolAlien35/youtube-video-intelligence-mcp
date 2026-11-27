# Quota accounting

## Source

[Reference](https://developers.google.com/youtube/v3/determine_quota_cost) and project SRS v1.0.

## Ingested by / date

Harsh (Person C), 24 November 2026, AI-assisted draft for review.

## Summary

Search uses a dedicated daily bucket.
Count one search call for each requested page.
Budget common operations separately.
Reset the counters at midnight Pacific time.
Reserve the whole bounded workflow before its first request.

## Key facts

The calculator lists 100 default daily search calls and 10,000 common units. The SRS sets project caps at 20 and 2,000 respectively.

## Relevance

NFR-01–07b

## Open questions / risks

The §6.1 table says 100 units for search. Confirm the wording through change control; a two-page search consumes two dedicated calls.

## Links

[[test_strategy]] · [[requirements_rtm]]
