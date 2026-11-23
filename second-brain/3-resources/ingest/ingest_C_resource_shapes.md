# Raw provider responses

## Source

[Reference](https://developers.google.com/youtube/v3/docs/videos) and project SRS v1.0.

## Ingested by / date

Harsh (Person C), 24 November 2026, AI-assisted draft for review.

## Summary

Read title, optional tags and defaultAudioLanguage from snippet.
Parse duration from contentDetails.
Preserve optional numeric strings in statistics until normalized.
Search returns resource references and a continuation token.
Map the error reason at the boundary.

## Key facts

[Search](https://developers.google.com/youtube/v3/docs/search/list) limits pages to 50 results. [Errors](https://developers.google.com/youtube/v3/docs/errors) distinguishes forbidden from quotaExceeded even when both use 403.

## Relevance

IF-12–16b; DATA-01–06

## Open questions / risks

Keep live/upcoming duration and missing language cases in fixtures.

## Links

[[test_strategy]] · [[requirements_rtm]]
