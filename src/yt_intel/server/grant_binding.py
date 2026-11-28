"""Bridge the async OAuth routes to A's synchronous, principal-scoped GrantRepo."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from sqlalchemy.engine import Engine

from yt_intel.common import Principal
from yt_intel.config import Settings
from yt_intel.google_oauth.client import GoogleWebClient
from yt_intel.policy.ledger import ComplianceLedger
from yt_intel.security.crypto import EncryptedBlob, KeyRing
from yt_intel.storage import get_engine, init_db, session_scope
from yt_intel.storage.grants import GrantRepo
from yt_intel.storage.scoped import ScopedSession

from .oauth_routes import GoogleLink


class StoredGrants:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def save(
        self, principal: Principal, sub: str, scopes: frozenset[str], blob: EncryptedBlob
    ) -> None:
        with session_scope(self.engine) as session:
            GrantRepo(ScopedSession(session, principal)).save(principal, sub, sorted(scopes), blob)

    def get(self, principal: Principal, account_ref: str) -> tuple[str, EncryptedBlob] | None:
        with session_scope(self.engine) as session:
            row = GrantRepo(ScopedSession(session, principal)).get(
                principal, account_ref=account_ref
            )
            if row is None:
                return None
            if row.ciphertext is None or row.nonce is None or row.key_version is None:
                raise ValueError("Incomplete encrypted grant")
            return row.account_ref, EncryptedBlob(row.key_version, row.nonce, row.ciphertext)

    def delete(self, principal: Principal, account_ref: str) -> None:
        with session_scope(self.engine) as session:
            GrantRepo(ScopedSession(session, principal)).delete(principal, account_ref=account_ref)


@asynccontextmanager
async def configured_link(
    settings: Settings, provided: GoogleLink | None
) -> AsyncIterator[GoogleLink | None]:
    if provided is not None or not settings.google_client_id:
        yield provided
        return
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
                StoredGrants(engine),
                lambda event, p: ledger.record(event, principal=p),
            )
    finally:
        engine.dispose()
