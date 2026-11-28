import pytest

from yt_intel.common import errors
from yt_intel.server.errors import HTTP_STATUS

pytestmark = [pytest.mark.unit, pytest.mark.security]


@pytest.mark.parametrize(
    "error,status",
    [
        (errors.AuthRequiredError, 401),
        (errors.InvalidTokenError, 401),
        (errors.ForbiddenOriginError, 403),
        (errors.ReauthorizationRequiredError, 401),
        (errors.TenantViolationError, 403),
        (errors.PolicyGateClosedError, 403),
    ],
)
def test_public_auth_error(error, status):
    exc = error()
    assert HTTP_STATUS[exc.code] == status
    assert exc.to_dict("r")["details"] is None
    if error is errors.PolicyGateClosedError:
        assert exc.to_dict()["code"] == "policy_gate_closed"
