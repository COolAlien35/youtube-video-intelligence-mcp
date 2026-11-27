# Evaluating a ranked top ten

## Source

[Reference](https://scikit-learn.org/stable/modules/model_evaluation.html#normalized-discounted-cumulative-gain) and project SRS v1.0.

## Ingested by / date

Harsh (Person C), 24 November 2026, AI-assisted draft for review.

## Summary

Label candidates before scoring.
Precision at K counts relevant results in the first K positions.
Discounted gain rewards relevant results appearing earlier.
Normalize using the best ordering for that query.
Record both scores per query.

## Key facts

The evaluation reference defines ideal-order normalization. The test strategy proposes exponential gain and explicit handling of queries with no positive labels.

## Relevance

TQ-28–34

## Open questions / risks

Agree on the relevance rubric and freeze a held-out synthetic set.

## Links

[[test_strategy]] · [[requirements_rtm]]
