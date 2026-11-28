from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from mcp.server import MCPServer
from mcp.server.transport_security import TransportSecuritySettings

from yt_intel import __version__
from yt_intel.common import AppError
from yt_intel.common.logging import configure_logging
from yt_intel.config import Settings, get_settings, validate_settings
from yt_intel.tools.registry import register_tools

from .auth import AuthMiddleware, JwtVerifier
from .errors import handle_app_error
from .grant_binding import configured_link
from .guards import require_local_environment
from .oauth_routes import GoogleLink, install_routes
from .origin import OriginMiddleware
from .request_id import RequestIDMiddleware


def create_app(
    settings: Settings | None = None,
    *,
    verifier: JwtVerifier | None = None,
    google_link: GoogleLink | None = None,
) -> FastAPI:
    config = get_settings() if settings is None else settings
    require_local_environment(config.environment)
    validate_settings(config)
    configure_logging(config.log_level)
    server: MCPServer[None] = MCPServer("YouTube Video Intelligence", version=__version__)
    register_tools(server)
    loopback = ["localhost", "127.0.0.1", "[::1]"]
    transport = server.streamable_http_app(
        stateless_http=True,
        json_response=True,
        transport_security=TransportSecuritySettings(
            allowed_hosts=loopback + [f"{host}:*" for host in loopback],
            allowed_origins=config.allowed_origins,
        ),
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        async with (
            configured_link(config, google_link) as link,
            transport.router.lifespan_context(transport),
        ):
            app.state.google_link = link
            yield

    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.add_exception_handler(AppError, handle_app_error)
    app.add_middleware(
        AuthMiddleware, verifier=verifier or JwtVerifier.from_settings(config), config=config
    )
    app.add_middleware(OriginMiddleware, allowed=config.allowed_origins)
    app.add_middleware(RequestIDMiddleware)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    app.state.google_link = google_link
    install_routes(app, config)
    app.mount("/", transport)
    return app
