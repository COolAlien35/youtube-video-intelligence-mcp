import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from urllib.parse import urlsplit

from fastapi import FastAPI
from mcp.server import MCPServer
from mcp.server.transport_security import TransportSecuritySettings

from yt_intel import __version__
from yt_intel.account.loader import AccountSignalsLoader
from yt_intel.common import AppError
from yt_intel.common.logging import configure_logging
from yt_intel.config import Settings, get_settings, validate_settings
from yt_intel.provider.factory import build_provider
from yt_intel.quota import PrincipalLimiter, QuotaPlanner, QuotaService
from yt_intel.services.account_signal_adapter import AccountSignalAdapter
from yt_intel.services.engagement import EngagementService
from yt_intel.services.engagement_fixture import FixtureSignalsLoader
from yt_intel.storage import get_engine, init_db
from yt_intel.tools.registry import register_tools

from .auth import AuthMiddleware, JwtVerifier
from .errors import handle_app_error
from .grant_binding import configured_link
from .oauth_routes import GoogleLink, install_routes
from .origin import OriginMiddleware
from .request_id import RequestIDMiddleware


def create_app(
    settings: Settings | None = None,
    *,
    verifier: JwtVerifier | None = None,
    google_link: GoogleLink | None = None,
    account_loader: AccountSignalsLoader | None = None,
) -> FastAPI:
    config = get_settings() if settings is None else settings
    validate_settings(config)
    configure_logging(config.log_level)
    # RequestIDMiddleware emits path-only access logs. OAuth query strings are private.
    logging.getLogger("uvicorn.access").disabled = True
    server: MCPServer[None] = MCPServer("YouTube Video Intelligence", version=__version__)
    register_tools(server)
    loopback = ["localhost", "127.0.0.1", "[::1]"]
    hosts = loopback + [f"{host}:*" for host in loopback]
    if config.google_redirect_uri:
        callback = urlsplit(config.google_redirect_uri)
        if (
            callback.path != "/oauth/google/callback"
            or callback.query
            or callback.fragment
            or callback.username is not None
            or not callback.hostname
        ):
            raise ValueError("google_redirect_uri must point exactly to /oauth/google/callback")
        hosts.append(callback.netloc)
    transport = server.streamable_http_app(
        stateless_http=True,
        json_response=True,
        transport_security=TransportSecuritySettings(
            allowed_hosts=hosts,
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
            engine = get_engine(config)
            try:
                init_db(engine)
                provider = build_provider(config)
                planner = QuotaPlanner(QuotaService(engine, config))
                app.state.engagement = EngagementService(
                    AccountSignalAdapter(account_loader)
                    if account_loader is not None
                    else FixtureSignalsLoader(engine, link, provider, planner, config),
                    provider,
                    engine,
                    planner,
                    PrincipalLimiter(engine, config),
                    link.lock if link else None,
                )
                yield
            finally:
                engine.dispose()

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
