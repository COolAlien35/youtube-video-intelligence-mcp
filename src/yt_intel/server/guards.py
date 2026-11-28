from yt_intel.common import Principal
from yt_intel.common.errors import AuthRequiredError

from .auth import principal_var


def get_principal() -> Principal:
    principal = principal_var.get()
    if principal is None:
        raise AuthRequiredError()
    return principal
