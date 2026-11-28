# Engagement analysis

An authenticated user can describe a connected fixture account through `engagement_analysis`. A request supplies a source and two period boundaries. Playlist items also require the owned playlist ID. For example:

```json
{"source":"liked_videos","period":{"start":"2026-01-01","end":"2026-02-01"}}
```

| Source | Unit | Timestamp used |
|---|---|---|
| liked_videos | videos | video_published_at, the video's publication date. The API exposes only the 1,000 most recent likes and supplies no date for the act of liking. |
| subscriptions | subscriptions | subscription_created_at, the creation date of the subscription |
| playlist_items | playlist items | playlist_item_added_at, the date the item was added to the specified playlist |

## Reading the result

Dates without a time denote midnight UTC. Full timestamps require an offset. Both period boundaries are normalized to UTC. The start is inclusive and the end exclusive. Each valid record counts once, including separate playlist entries for the same video. Missing and invalid timestamps across the fetched sample increase excluded_invalid_timestamp. Daily trends list observed UTC dates. An absent day has no observations in this sample.

The channel distribution returns up to ten IDs ordered by count descending, then ID ascending. Each share is its count divided by the period count. The remaining buckets contribute to other_count and other_share. distinct_known excludes missing identifiers. Categories use supplied IDs with an optional provider-supplied name. Missing metadata goes in unknown. The fixture path makes no category-name lookup.

| Duration bucket | Integer seconds |
|---|---|
| under_10m | 0–599 |
| 10_to_under_30m | 600–1,799 |
| 30_to_60m | 1,800–3,600 |
| over_60m | 3,601 and above |
| unknown | Missing, negative or invalid duration |

Subscriptions carry neither duration nor video category. Both sections return not_applicable. Playlist enrichment considers the first 100 distinct video IDs in source order, fetches up to 50 per batch and reports the number selected and available. A missing video detail does not remove a valid dated item. Duration bands count videos or entries by recorded video length. They do not measure minutes viewed.

The default comparison uses the immediately preceding window of equal length. An explicit compare_to uses the same start/end rules. Absolute change is current minus earlier count. Relative change divides that difference by the earlier count. Zero earlier observations yield null and a qualifier. A current window with no valid observations sets insufficient_data and gives a reason.

Coverage reports the source, unit, time basis, fetched count, provider-reported total when available, item cap, truncation and reason, fetch time and cache status. A missing total is unknown. Partial coverage limits every metric and comparison. Results describe the accessible sample only. [Input schema](tools/engagement_analysis.input.schema.json) · [Output schema](tools/engagement_analysis.output.schema.json)
