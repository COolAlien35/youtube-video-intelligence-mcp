import time

import pytest
from tests.support.b_auth import FakeIssuer

from yt_intel.common.errors import InvalidTokenError

pytestmark = [pytest.mark.unit, pytest.mark.security]


def test_cache_and_claims():
    issuer = FakeIssuer()
    verifier = issuer.verifier()
    assert verifier.verify(issuer.mint()).key == "https://issuer.example|one"
    assert verifier.verify(issuer.mint("two")).subject == "two"
    for claims in [
        {"exp": 1},
        {"nbf": int(time.time()) + 600},
        {"iss": "wrong"},
        {"aud": "wrong"},
        {"sub": ""},
        {"kid": "absent"},
    ]:
        with pytest.raises(InvalidTokenError):
            verifier.verify(issuer.mint(**claims))
    with pytest.raises(InvalidTokenError):
        verifier.verify(FakeIssuer().mint())
    assert issuer.fetches == 1
