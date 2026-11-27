import io
import json
import logging
from contextlib import redirect_stderr

import pytest

from yt_intel.common import request_id_var
from yt_intel.common.logging import configure_logging
from yt_intel.common.timeutil import parse_rfc3339_utc

pytestmark = [pytest.mark.unit, pytest.mark.security]


@pytest.fixture
def capture():
    root = logging.getLogger()
    handlers = root.handlers[:]
    level = root.level
    for handler in handlers:
        root.removeHandler(handler)
    rid = request_id_var.set("FAKE_request")
    try:
        with redirect_stderr(io.StringIO()) as stream:
            configure_logging()
            yield stream
    finally:
        request_id_var.reset(rid)
        for handler in root.handlers[:]:
            root.removeHandler(handler)
            handler.close()
        for handler in handlers:
            root.addHandler(handler)
        root.setLevel(level)


@pytest.mark.parametrize(
    "key",
    [
        "token",
        "secret",
        "password",
        "Authorization",
        "api_key",
        "refresh_token",
        "access_token",
        "client_secret",
    ],
)
def test_nested_fields_and_formatted_messages(capture, key):
    logging.getLogger("worker").warning(
        "%s=%s", key, "FAKE_private", extra={"batch": [{key: "FAKE_nested"}]}
    )
    data = json.loads(capture.getvalue())
    assert "FAKE_private" not in capture.getvalue() and "FAKE_nested" not in capture.getvalue()
    assert data["extra"]["batch"][0][key] == "[REDACTED]"
    assert data["request_id"] == "FAKE_request" and data["logger"] == "worker"
    assert data["level"] == "WARNING" and parse_rfc3339_utc(data["timestamp"])


@pytest.mark.parametrize(
    "token",
    [
        "Bearer FAKE_bearer",
        "AIza" + "FAKE_" + "x" * 31,
        "ya29." + "FAKE_access",
        "eyJ" + "FAKE_head.FAKE_payload.FAKE_sig",
    ],
)
def test_exception_and_text_patterns(capture, token):
    try:
        raise ValueError(token)
    except ValueError:
        logging.getLogger("worker").exception("upstream: %s", token)
    event = json.loads(capture.getvalue())
    assert token not in capture.getvalue()
    assert "[REDACTED]" in event["message"] and "[REDACTED]" in event["exception"]


def test_reconfigure_and_private_fields(capture):
    with redirect_stderr(capture):
        configure_logging()
        handler = logging.getLogger().handlers[0]
        configure_logging("DEBUG")
    assert logging.getLogger().handlers == [handler]
    logging.getLogger("worker").debug(
        "line one\nline two",
        extra={"request_body": "FAKE_body", "headers": {"other": "FAKE_header"}},
    )
    assert len(capture.getvalue().splitlines()) == 1
    data = json.loads(capture.getvalue())
    assert "extra" not in data and data["message"].endswith("line two")
