import unicodedata

import pytest
from tests.support.injection_payloads import PAYLOADS

from yt_intel.common import errors
from yt_intel.common.untrusted import sanitize_untrusted
from yt_intel.server.errors import HTTP_STATUS


@pytest.mark.parametrize(
    "payload",
    PAYLOADS
    + (
        "e\u0301",
        "a\nb\tc",
    ),
)
def test_display(payload):
    value = sanitize_untrusted(payload, max_len=32)
    assert len(value) <= 32 and unicodedata.is_normalized("NFC", value)
    assert value == sanitize_untrusted(value, max_len=32)
    assert not set(value) & set("\u202e\u2066\u2069\x00")
    if len(payload) > 32:
        assert value.endswith("…")


@pytest.mark.parametrize(
    "name",
    "ChannelRequired WriteScopeRequired ProposalNotFound ProposalExpired ApprovalInvalid InvalidTransition ConstraintViolation OutcomeUncertain ReconciliationAmbiguous".split(),
)
def test_errors(name):
    err = getattr(errors, name + "Error")()
    assert HTTP_STATUS[err.code] >= 400 and err.to_dict("fixture")["request_id"] == "fixture"
    if name in {"ChannelRequired", "WriteScopeRequired"}:
        assert err.details["next_step"]
