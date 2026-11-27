"""Bridge the async OAuth routes to A's synchronous, principal-scoped GrantRepo."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from importlib import import_module
from typing import Protocol, cast

import httpx
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from yt_intel.common import Principal
from yt_intel.config import Settings
from yt_intel.google_oauth.client import GoogleWebClient
from yt_intel.policy.ledger import ComplianceLedger
from yt_intel.security.crypto import EncryptedBlob, KeyRing
from yt_intel.storage import GoogleGrantRecord, get_engine, init_db, session_scope

from .oauth_routes import GoogleLink


class Repo(Protocol):
    def save(
        self, principal: Principal, google_sub: str, scopes: list[str], blob: EncryptedBlob
    ) -> object: ...
    def get(self, principal: Principal) -> GoogleGrantRecord | None: ...
    def delete(self, principal: Principal) -> object: ...


class RepoFactory(Protocol):
    def __call__(self, session: Session) -> Repo: ...


class StoredGrants:
    def __init__(self, engine: Engine, factory: RepoFactory) -> None:
        self.engine = engine
        self.factory = factory

    def save(
        self, principal: Principal, sub: str, scopes: frozenset[str], blob: EncryptedBlob
    ) -> None:
        with session_scope(self.engine) as session:
            self.factory(session).save(principal, sub, sorted(scopes), blob)

    def get(self, principal: Principal) -> tuple[str, EncryptedBlob] | None:
        with session_scope(self.engine) as session:
            row = self.factory(session).get(principal)
            if row is None:
                return None
            if row.ciphertext is None or row.nonce is None or row.key_version is None:
                raise ValueError("Incomplete encrypted grant")
            return row.account_ref, EncryptedBlob(row.key_version, row.nonce, row.ciphertext)

    def delete(self, principal: Principal) -> None:
        with session_scope(self.engine) as session:
            self.factory(session).delete(principal)


@asynccontextmanager
async def configured_link(
    settings: Settings, provided: GoogleLink | None
) -> AsyncIterator[GoogleLink | None]:
    if provided is not None or not settings.google_client_id:
        yield provided
        return
    try:
        factory = cast("RepoFactory", import_module("yt_intel.storage.grants").GrantRepo)
    except ModuleNotFoundError as exc:
        raise RuntimeError("Google linking requires the Phase 3 GrantRepo") from exc
    ring = KeyRing.from_settings(settings)
    engine = get_engine(settings)
    try:
        init_db(engine)
        ledger = ComplianceLedger(engine)
        async with httpx.AsyncClient(timeout=10, follow_redirects=False) as http:
            client = GoogleWebClient(
                settings.google_client_id,
                settings.google_client_secret.get_secret_value(),
                settings.google_redirect_uri,
                http,
            )
            yield GoogleLink(
                client,
                ring,
                StoredGrants(engine, factory),
                lambda event, p: ledger.record(event, principal=p),
            )
    finally:
        engine.dispose()
