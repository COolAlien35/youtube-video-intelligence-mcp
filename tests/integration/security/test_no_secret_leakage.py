import io
import logging
from urllib.parse import parse_qs, urlsplit

import pytest

from yt_intel.common.logging import _JsonFormatter
from yt_intel.security.crypto import decrypt_token

pytestmark = pytest.mark.security


async def test_oauth_success_and_failure_leave_no_secrets_in_emitted_logs_or_errors(
    security_app, connect_google, principal_a
):
    ctx = security_app
    output = io.StringIO()
    handler = logging.StreamHandler(output)
    handler.setFormatter(_JsonFormatter())
    root = logging.getLogger()
    root.addHandler(handler)
    try:
        result, query, code = await connect_google()
        blob = ctx.store.get(principal_a, "FAKE_google_alpha")[1]
        refresh = decrypt_token(blob, principal=principal_a, keyring=ctx.ring)
        access = (await ctx.google.refresh(refresh)).access_token
        bearer = ctx.issuer.mint()
        failed = await ctx.browser.get(
            "/oauth/google/callback",
            params={"code": code, "state": query["state"][0]},
        )
        assert failed.status_code == 401
        # Exercise an invalid_grant path through the real callback handler.
        start = await ctx.browser.get(
            "/oauth/google/start", headers={"Authorization": "Bearer " + bearer}
        )
        pending = parse_qs(urlsplit(start.headers["location"]).query)
        bad_code = ctx.google.authorize(pending["code_challenge"][0])
        ctx.google.revoked = True
        invalid_grant = await ctx.browser.get(
            "/oauth/google/callback", params={"code": bad_code, "state": pending["state"][0]}
        )
        assert invalid_grant.status_code == 401
        secrets = {
            refresh,
            access,
            bearer,
            code,
            bad_code,
            query["state"][0],
            pending["state"][0],
            ctx.config.google_client_secret.get_secret_value(),
        }
        rendered = output.getvalue()
        assert "HTTP request" in rendered and "[REDACTED]" in rendered
        public = rendered + result.text + failed.text + invalid_grant.text
        for secret in secrets:
            assert secret and secret not in public
        assert "Traceback" not in failed.text + invalid_grant.text
    finally:
        root.removeHandler(handler)
        handler.close()
