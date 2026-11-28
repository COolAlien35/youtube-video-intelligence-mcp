"""Unit tests verifying LiveAccountProvider refuses access while gates are closed."""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import pytest

from yt_intel.common.errors import AppError, ErrorCode
from yt_intel.config.settings import Settings
from yt_intel.provider.account_live import LiveAccountProvider, PolicyGateClosedError

if TYPE_CHECKING:
    from yt_intel.common.types import Principal


class _StubTokenSource:
    def access_token(self, principal: Principal, *, required_scopes: tuple[str, ...]) -> str:
        raise AssertionError("TokenSource must never be called when gates are closed")


def test_live_account_provider_refuses_when_gates_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fail_client(*args: object, **kwargs: object) -> object:
        raise AssertionError("HTTP client must never be constructed when policy gates are closed")

    monkeypatch.setattr(httpx, "AsyncClient", _fail_client)

    default_settings = Settings(_env_file=None)
    with pytest.raises(PolicyGateClosedError) as exc:
        LiveAccountProvider(default_settings, _StubTokenSource())
    assert isinstance(exc.value, AppError)
    assert exc.value.code is ErrorCode.POLICY_GATE_CLOSED

    partial_settings = Settings(_env_file=None, pol_04_open=True, pol_05_open=False)
    with pytest.raises(PolicyGateClosedError):
        LiveAccountProvider(partial_settings, _StubTokenSource())

    gates_only = Settings(
        _env_file=None,
        pol_04_open=True,
        pol_05_open=True,
        live_youtube_enabled=False,
    )
    with pytest.raises(PolicyGateClosedError):
        LiveAccountProvider(gates_only, _StubTokenSource())
