"""YouTube Data API v3 quota costs (SRS §6.1).

Sources:
  - Official YouTube Data API quota calculator: https://developers.google.com/youtube/v3/determine_your_quota_usage
  - SRS §6.1 cost table

TBC items are marked explicitly and must be verified against the official calculator
before Phase 3 begins. Post any discrepancy as a type:change-request issue.
"""

from __future__ import annotations

from .service import WorkflowCost

# ---------------------------------------------------------------------------
# Cost table (SRS §6.1, verified against official quota calculator)
# ---------------------------------------------------------------------------
# Common unit costs (shared bucket, daily cap default: 2000)
_COMMON_COSTS: dict[str, int] = {
    "videos.list": 1,
    "channels.list": 1,
    "captions.list": 50,  # disabled by default in Phase 2
    "captions.download": 200,  # disabled by default in Phase 2
    "playlists.insert": 50,
    "playlistItems.insert": 50,  # 50 per item — multiply by count
    # TBC: verify the following on the official YouTube quota calculator
    # https://developers.google.com/youtube/v3/determine_your_quota_usage
    "playlists.list": 1,  # TBC — confirm with team
    "playlistItems.list": 1,  # TBC — confirm with team
    "subscriptions.list": 1,  # TBC — confirm with team
}

# Search call costs (dedicated bucket, daily cap default: 20)
_SEARCH_COSTS: dict[str, int] = {
    "search.list": 1,  # 100 units on the common bucket *and* 1 search call
}

# search.list also burns 100 common units per call (SRS §6.1)
_SEARCH_COMMON_UNITS: int = 100


def cost_of(operation: str, count: int = 1) -> WorkflowCost:
    """Return the :class:`WorkflowCost` for *operation* repeated *count* times.

    Raises :class:`ValueError` for unknown operations or non-positive *count*.
    Never returns a silent zero — an unknown operation is always an error.
    """
    if count <= 0:
        raise ValueError(f"count must be a positive integer, got {count!r}")

    if operation in _SEARCH_COSTS:
        search_calls = _SEARCH_COSTS[operation] * count
        common_units = _SEARCH_COMMON_UNITS * count
        return WorkflowCost(common_units=common_units, search_calls=search_calls)

    if operation in _COMMON_COSTS:
        return WorkflowCost(common_units=_COMMON_COSTS[operation] * count)

    raise ValueError(
        f"Unknown YouTube Data API operation: {operation!r}. "
        "Add it to quota/costs.py with a TBC note if unverified, "
        "or raise a change-request issue."
    )
