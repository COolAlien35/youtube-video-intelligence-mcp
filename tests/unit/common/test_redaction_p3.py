import logging

import pytest

from yt_intel.common.logging import _JsonFormatter

pytestmark = [pytest.mark.unit, pytest.mark.security]


@pytest.mark.parametrize(
    "field",
    [
        "Authorization",
        "code",
        "state",
        "code_verifier",
        "client_secret",
        "access_token",
        "refresh_token",
    ],
)
def test_oauth_values_redacted(field):
    record = logging.makeLogRecord(
        {
            "msg": "callback?%s=%s",
            "args": (field, "FAKE_sensitive"),
            "nested": [{field: "FAKE_sensitive"}],
        }
    )
    out = _JsonFormatter().format(record)
    assert "FAKE_sensitive" not in out and "[REDACTED]" in out
