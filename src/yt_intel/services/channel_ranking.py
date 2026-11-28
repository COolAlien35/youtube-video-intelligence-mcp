"""Offline TF-IDF ranker implementing the proposed shared ranking contract."""

import math
import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class Document:
    id: str
    title: str
    description: str
    tags: tuple[str, ...]
    category: str | None = None


@dataclass(frozen=True)
class WeightProfile:
    title: float
    description: float
    tags: float
    category: float


@dataclass(frozen=True)
class RankedItem:
    id: str
    score: float
    factors: dict[str, float]
    top_terms: tuple[str, ...]


def _vectors(texts: list[str]) -> list[dict[str, float]]:
    counts = [Counter(re.findall(r"[^\W_]+", text.casefold())) for text in texts]
    df = Counter(term for doc in counts for term in doc)
    vectors = []
    for doc in counts:
        vec = {
            term: n * (1 + math.log((1 + len(texts)) / (1 + df[term]))) for term, n in doc.items()
        }
        norm = math.sqrt(sum(v * v for v in vec.values()))
        vectors.append({term: v / norm for term, v in vec.items()})
    return vectors


class RankingEngine:
    def rank(
        self,
        seed: Document,
        candidates: Sequence[Document],
        *,
        weights: WeightProfile,
        top_k: int = 10,
    ) -> list[RankedItem]:
        docs = [seed, *candidates]
        factors: list[dict[str, float]] = [{} for _ in candidates]
        terms: list[Counter[str]] = [Counter() for _ in candidates]
        for field, weight, texts in (
            ("title", weights.title, [d.title for d in docs]),
            ("description", weights.description, [d.description for d in docs]),
            ("keywords", weights.tags, [" ".join(d.tags) for d in docs]),
        ):
            seed_vec, *others = _vectors(texts)
            for i, other in enumerate(others):
                overlap = {t: weight * v * seed_vec[t] for t, v in other.items() if t in seed_vec}
                factors[i][field] = sum(overlap.values())
                terms[i].update(overlap)
        if weights.category:
            for i, candidate in enumerate(candidates):
                factors[i]["category"] = (
                    weights.category
                    if seed.category and candidate.category == seed.category
                    else 0.0
                )
        items = [
            RankedItem(
                d.id, sum(f.values()), f, tuple(sorted(t, key=lambda term: (-t[term], term))[:3])
            )
            for d, f, t in zip(candidates, factors, terms, strict=True)
        ]
        return sorted(items, key=lambda item: (-item.score, item.id))[:top_k]


class VideoRankingEngine(RankingEngine):
    """Apply the video profile and renormalize when the seed supplies no tags."""

    def weights_for(self, seed: Document) -> WeightProfile:
        if any(tag.strip() for tag in seed.tags):
            return WeightProfile(0.50, 0.30, 0.15, 0.05)
        return WeightProfile(0.50 / 0.85, 0.30 / 0.85, 0, 0.05 / 0.85)
