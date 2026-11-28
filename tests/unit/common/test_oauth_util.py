import base64
import re

import pytest

from yt_intel.common import oauth_util

pytestmark = [pytest.mark.unit, pytest.mark.security]


def test_random_values():
    first = oauth_util.new_state()
    assert len(base64.urlsafe_b64decode(first + "=")) >= 32
    assert first != oauth_util.new_state()
    v, ch = oauth_util.new_pkce_pair()
    assert re.fullmatch(r"[A-Za-z0-9_-]{43,128}", v)
    assert len(ch) == 43 and v != ch


def test_appendix_b(monkeypatch):
    verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
    monkeypatch.setattr(oauth_util.secrets, "token_urlsafe", lambda size: verifier)
    assert oauth_util.new_pkce_pair() == (verifier, "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM")


def test_state_comparison():
    assert oauth_util.constant_time_equals("a", "a")
    assert not oauth_util.constant_time_equals("a", "é")
