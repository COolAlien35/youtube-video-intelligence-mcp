"""Pydantic settings and startup validation for yt_intel."""

from __future__ import annotations

import base64
import binascii
import json
from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# TBC — confirm with team which origins Claude Desktop actually sends before relying on defaults.
_DEFAULT_DEV_ORIGINS: list[str] = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]


class Settings(BaseSettings):
    """Application settings loaded from environment variables (prefix ``YT_INTEL_``)."""

    model_config = SettingsConfigDict(
        env_prefix="YT_INTEL_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: Literal["dev", "test", "prod"] = "dev"
    host: str = "127.0.0.1"
    port: int = 8000
    allowed_origins: list[str] = Field(default_factory=lambda: list(_DEFAULT_DEV_ORIGINS))
    log_level: str = "INFO"
    data_dir: Path = Path("./var")
    database_url: str = ""
    fixtures_dir: Path | None = None
    quota_common_daily_cap: int = 2000
    quota_search_daily_cap: int = 20
    max_concurrent_workflows_per_principal: int = 2
    max_workflow_starts_per_minute: int = 5
    live_youtube_enabled: bool = False

    # Phase 3: Auth, OAuth, token encryption, HTTPS/proxy, and policy gates
    supabase_issuer: str = ""
    supabase_jwks_url: str = ""
    supabase_audience: str = "authenticated"
    google_client_id: str = ""
    google_client_secret: SecretStr = SecretStr("")
    google_redirect_uri: str = ""
    token_keys: SecretStr = SecretStr("")
    active_token_key_version: int = 1
    require_https: bool = False
    trust_proxy_headers: bool = False
    pol_01_open: bool = False
    pol_02_open: bool = False
    pol_03_open: bool = False
    pol_04_open: bool = False
    pol_05_open: bool = False
    pol_06_open: bool = False
    pol_07_open: bool = False
    pol_08_open: bool = False

    @model_validator(mode="after")
    def _derive_database_url(self) -> Settings:
        """Derive SQLite database_url from data_dir unless explicitly overridden."""
        if not self.database_url:
            db_path = (self.data_dir / "yt_intel.db").as_posix()
            self.database_url = f"sqlite:///{db_path}"
        return self

    def __repr__(self) -> str:
        """Return a safe representation that never exposes secret values."""
        safe_fields: list[str] = []
        for name, field_info in type(self).model_fields.items():
            value = getattr(self, name)
            if isinstance(value, SecretStr) or field_info.annotation is SecretStr:
                safe_fields.append(f"{name}=SecretStr('**********')")
            else:
                safe_fields.append(f"{name}={value!r}")
        return f"{type(self).__name__}({', '.join(safe_fields)})"


def _is_valid_origin(origin: str) -> bool:
    """Return True if *origin* is a well-formed HTTP(S) origin without path/query/fragment."""
    if not origin or origin == "*" or "*" in origin:
        return False
    parsed = urlparse(origin)
    if parsed.scheme not in {"http", "https"}:
        return False
    if not parsed.netloc:
        return False
    return not (parsed.path not in {"", "/"} or parsed.params or parsed.query or parsed.fragment)


def _is_valid_http_url(url: str, *, require_https: bool = False) -> bool:
    """Return True if *url* is a well-formed HTTP(S) URL with a network location."""
    parsed = urlparse(url)
    allowed_schemes = {"https"} if require_https else {"http", "https"}
    return parsed.scheme in allowed_schemes and bool(parsed.netloc)


def parse_token_keys(raw: str) -> dict[int, bytes]:
    """Parse a JSON mapping of ``{version: base64_32byte_key}`` without leaking secrets."""
    if not raw.strip():
        raise ValueError("token_keys must not be empty")
    try:
        loaded = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("token_keys must be valid JSON") from exc

    if not isinstance(loaded, dict) or not loaded:
        raise ValueError("token_keys must be a non-empty JSON object")

    parsed: dict[int, bytes] = {}
    for raw_version, raw_key in loaded.items():
        if not isinstance(raw_version, str) or not raw_version.isdigit():
            raise ValueError("token_keys version keys must be positive integer strings")
        version = int(raw_version)
        if version <= 0:
            raise ValueError("token_keys version keys must be positive integers")
        if not isinstance(raw_key, str) or not raw_key.strip():
            raise ValueError(f"token_keys[{version}] must be a non-empty base64 string")
        try:
            key_bytes = base64.b64decode(raw_key, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError(f"token_keys[{version}] is not valid base64") from exc
        if len(key_bytes) != 32:
            raise ValueError(f"token_keys[{version}] must decode to exactly 32 bytes")
        parsed[version] = key_bytes

    return parsed


def validate_settings(settings: Settings) -> None:
    """Fail fast if *settings* violate safety, auth, or structural invariants."""
    if settings.port <= 0 or settings.port > 65535:
        raise ValueError("port must be between 1 and 65535")

    if settings.quota_common_daily_cap <= 0:
        raise ValueError("quota_common_daily_cap must be greater than 0")

    if settings.quota_search_daily_cap <= 0:
        raise ValueError("quota_search_daily_cap must be greater than 0")

    if settings.max_concurrent_workflows_per_principal <= 0:
        raise ValueError("max_concurrent_workflows_per_principal must be greater than 0")

    if settings.max_workflow_starts_per_minute <= 0:
        raise ValueError("max_workflow_starts_per_minute must be greater than 0")

    if settings.environment == "prod" and not settings.data_dir.is_absolute():
        raise ValueError("data_dir must be an absolute path in prod")

    for origin in settings.allowed_origins:
        if "*" in origin:
            if settings.environment == "prod":
                raise ValueError("wildcard origins are prohibited in prod")
            raise ValueError("wildcard origins are not valid exact-match origins")
        if not _is_valid_origin(origin):
            raise ValueError(f"malformed origin URL: {origin!r}")

    if settings.live_youtube_enabled:
        raise ValueError("live_youtube_enabled=True is prohibited in Phase 2 (policy gate closed)")

    if settings.active_token_key_version <= 0:
        raise ValueError("active_token_key_version must be greater than 0")

    raw_token_keys = settings.token_keys.get_secret_value()
    if raw_token_keys.strip():
        parsed_keys = parse_token_keys(raw_token_keys)
        if settings.active_token_key_version not in parsed_keys:
            raise ValueError("active_token_key_version is not present in token_keys")

    if settings.environment == "prod":
        missing: list[str] = []
        if not settings.supabase_issuer.strip():
            missing.append("supabase_issuer")
        if not settings.supabase_jwks_url.strip():
            missing.append("supabase_jwks_url")
        if not settings.supabase_audience.strip():
            missing.append("supabase_audience")
        if not settings.google_client_id.strip():
            missing.append("google_client_id")
        if not settings.google_client_secret.get_secret_value().strip():
            missing.append("google_client_secret")
        if not settings.google_redirect_uri.strip():
            missing.append("google_redirect_uri")
        if not raw_token_keys.strip():
            missing.append("token_keys")
        if missing:
            raise ValueError(f"missing required prod settings: {', '.join(missing)}")
        if not settings.require_https:
            raise ValueError("require_https must be True in prod")

    require_https_urls = settings.environment == "prod"
    if settings.supabase_jwks_url.strip() and not _is_valid_http_url(
        settings.supabase_jwks_url, require_https=require_https_urls
    ):
        raise ValueError("supabase_jwks_url must be a valid HTTP(S) URL")
    if settings.google_redirect_uri.strip() and not _is_valid_http_url(
        settings.google_redirect_uri, require_https=require_https_urls
    ):
        raise ValueError("google_redirect_uri must be a valid HTTP(S) URL")
    if settings.environment == "prod" and not _is_valid_http_url(
        settings.supabase_issuer, require_https=True
    ):
        raise ValueError("supabase_issuer must be a valid HTTPS URL in prod")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached application Settings instance."""
    return Settings()
