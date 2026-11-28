# Source timestamps in engagement analysis

Person D · 2026-11-28 · FR-4a–4k, DATA-16–21

ADR-11 limits engagement analysis to descriptive counts, trends, duration distributions and comparisons over accessible account data. A source determines which event a timestamp represents. A liked video's date belongs to publication, a subscription date belongs to its creation, and a playlist entry's date belongs to its addition. Switching that interpretation would change the question answered by a period comparison. [ADR-11](../../../docs/Architecture_Decision_Records_v1.0.md)

Normalize the instant before assigning its UTC day. A missing timestamp increments an exclusion count. A missing duration on an otherwise valid record belongs in the unknown duration bucket. Coverage travels with cached data so a repeated result preserves the original sample limits and fetch time. The stage review tracks integration with the shared loader and remaining isolation evidence. [Metric definitions](../../../docs/analytics.md) · [Stage review](../../../docs/stage_reviews/phase5_review.md)
