"""Pydantic settings and startup validation for yt_intel."""

from __future__ import annotations

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


def validate_settings(settings: Settings) -> None:
    """Fail fast if *settings* violate Phase 2 safety or structural invariants."""
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


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached application Settings instance."""
    return Settings()
