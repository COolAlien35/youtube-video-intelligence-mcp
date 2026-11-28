"""Account signals loader stub (implemented in PR 5)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from yt_intel.account.types import AccountSignals, SignalKind
    from yt_intel.common.types import Principal


class AccountSignalsLoader:
    """Loads principal-scoped account signals with cache, quota preflight, and coverage."""

    async def load(
        self,
        principal: Principal,
        want: frozenset[SignalKind],
        *,
        playlist_ids: Sequence[str] = (),
        like_cap: int = 1000,
        refresh: bool = False,
    ) -> AccountSignals:
        """Load requested account signals for *principal*."""
        raise NotImplementedError("AccountSignalsLoader.load is not implemented yet")
