import asyncio

import httpx
import pytest
from starlette.routing import Route
from tests.support.b_auth import FakeIssuer

from yt_intel import __version__
from yt_intel.common import AppError, ErrorCode
from yt_intel.config import Settings
from yt_intel.server.app import create_app
from yt_intel.server.errors import HTTP_STATUS

pytestmark = pytest.mark.unit
ORIGIN = "http://localhost:8000"


def settings(**kwargs):
    return Settings(_env_file=None, allowed_origins=[ORIGIN], **kwargs)


def test_health_errors_and_request_ids():
    issuer = FakeIssuer()
    app = create_app(settings(), verifier=issuer.verifier())

    async def unexpected(_):
        raise ValueError("private diagnostic FAKE_only")

    async def expected(_):
        raise AppError(ErrorCode.INVALID_INPUT, "Invalid ID")

    app.router.routes[:0] = [Route("/unexpected", unexpected), Route("/expected", expected)]

    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url=ORIGIN) as c:
            denied = await c.post("/mcp")
            assert (
                denied.status_code == 401
                and "resource_metadata" in denied.headers["www-authenticate"]
            )
            first = await c.get("/health")
            second = await c.get("/health", headers={"Origin": ORIGIN})
            assert first.json() == second.json() == {"status": "ok", "version": __version__}
            assert first.headers["x-request-id"] != second.headers["x-request-id"]
            for path, status, code in [
                ("/unexpected", 500, "INTERNAL_ERROR"),
                ("/expected", 400, "INVALID_INPUT"),
            ]:
                response = await c.get(path, headers={"Authorization": "Bearer " + issuer.mint()})
                assert response.status_code == status and response.json()["code"] == code
                assert response.json()["request_id"] == response.headers["x-request-id"]
                assert "FAKE_only" not in response.text and "Traceback" not in response.text

    asyncio.run(run())


@pytest.mark.security
@pytest.mark.parametrize("path", ["/health", "/mcp"])
@pytest.mark.parametrize(
    "headers", [[("Origin", ORIGIN + ".invalid")], [("Origin", ORIGIN), ("Origin", "")]]
)
def test_reject_origin(path, headers):
    async def run():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(create_app(settings())), base_url=ORIGIN
        ) as c:
            r = await c.post(path, headers=headers)
            assert r.status_code == 403 and r.json()["code"] == "FORBIDDEN"
            assert r.headers["x-request-id"] == r.json()["request_id"]

    asyncio.run(run())


@pytest.mark.security
def test_prod_requires_auth_settings(tmp_path):
    with pytest.raises(ValueError, match="missing required prod settings"):
        create_app(settings(environment="prod", data_dir=tmp_path))


def test_all_error_codes_mapped():
    assert set(HTTP_STATUS) == set(ErrorCode)
