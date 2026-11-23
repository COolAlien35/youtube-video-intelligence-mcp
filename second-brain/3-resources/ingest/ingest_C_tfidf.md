# Field-weighted metadata similarity

## Source

[Reference](https://scikit-learn.org/stable/modules/feature_extraction.html#tfidf-term-weighting) and project SRS v1.0.

## Ingested by / date

Harsh (Person C), 24 November 2026, AI-assisted draft for review.

## Summary

Count terms in each metadata field.
Scale terms by inverse document frequency over the chosen corpus.
Compare normalized vectors by cosine similarity.
Score the four fields separately to preserve their contributions.
Sort ties by canonical ID.

## Key facts

The vectorizer documentation defines TF-IDF and L2 normalization. SRS §4.1 assigns title 0.50, description 0.30, tags 0.15 and category 0.05.

## Relevance

FR-1a–1j

## Open questions / risks

Confirm missing-field weighting and freeze the vocabulary before comparing releases.

## Links

[[test_strategy]] · [[requirements_rtm]]
