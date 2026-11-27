"""Phase 3 replaces get_principal with verified request-scoped principal resolution.

Tool wrappers resolve the principal here before delegating to a handler. Credentials
and principal identity must never be accepted as client-supplied tool arguments.
"""

from yt_intel.common import Principal


def require_local_environment(environment: str) -> None:
    if environment == "prod":
        raise RuntimeError("Production requires Phase 3 authentication")


def get_principal() -> Principal | None:
    return None
