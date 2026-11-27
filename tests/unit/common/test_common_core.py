import asyncio
import json
from datetime import UTC, datetime
from uuid import UUID

import pytest

from yt_intel.common import (
    AppError,
    ErrorCode,
    FakeClock,
    Principal,
    SystemClock,
    get_request_id,
    new_request_id,
    set_request_id,
)

pytestmark = pytest.mark.unit


def test_error_defaults():
    assert AppError(ErrorCode.FORBIDDEN, "Denied").to_dict() == {
        "code": "FORBIDDEN",
        "message": "Denied",
        "details": None,
        "retryable": False,
        "retry_after": None,
        "request_id": None,
    }


@pytest.mark.security
def test_safe_error_output():
    err = AppError(
        ErrorCode.UPSTREAM_ERROR,
        "Bearer FAKE_message",
        details={"nested": [{"token": "FAKE_token"}]},
        retryable=True,
        retry_after=3,
    )
    try:
        raise ValueError("FAKE_private")
    except ValueError as cause:
        err.__cause__ = cause
    doc = err.to_dict("req")
    assert "FAKE_" not in json.dumps(doc)
    assert (doc["request_id"], doc["retryable"], doc["retry_after"]) == ("req", True, 3)


@pytest.mark.parametrize("bad", [object(), float("nan")])
def test_invalid_details(bad):
    with pytest.raises((TypeError, ValueError)):
        AppError(ErrorCode.INVALID_INPUT, "Invalid", details={"bad": bad})


@pytest.mark.parametrize("issuer,subject", [("", "s"), ("i", " "), ("i|x", "s")])
def test_invalid_principal(issuer, subject):
    with pytest.raises(ValueError):
        Principal(issuer, subject)


def test_principal_key():
    assert Principal("issuer", "sub|ject").key == "issuer|sub|ject"


def test_clock():
    clock = FakeClock(datetime.fromisoformat("2026-11-23T05:30:00+05:30"))
    assert clock.now() == datetime(2026, 11, 23, tzinfo=UTC)
    clock.advance(1.5)
    assert clock.now().microsecond == 500000 and clock.now().second == 1
    assert SystemClock().now().tzinfo is UTC
    with pytest.raises(ValueError):
        FakeClock(datetime(2026, 11, 23))


def test_context_isolation():
    async def task():
        rid = new_request_id()
        assert UUID(hex=rid).version == 4
        set_request_id(rid)
        await asyncio.sleep(0)
        assert get_request_id() == rid
        return rid

    async def run():
        set_request_id("parent")
        first, second = await asyncio.gather(task(), task())
        assert first != second and get_request_id() == "parent"
        set_request_id(None)
        assert get_request_id() is None

    asyncio.run(run())
